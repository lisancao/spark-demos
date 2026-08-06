/*
 * Plumbing, not DSV2. This class is the "storage layer" the connector talks to:
 * it knows how to find a CSV file, read its header, and split it into byte ranges.
 *
 * It is kept deliberately separate from the DSV2 classes so the API surface stays
 * visible. Everything Spark-specific lives in the other files.
 *
 * The split unit is a BYTE RANGE, not a row range, which is what real file
 * connectors use. Row ranges look simpler and are a trap: to know where row N
 * starts you have to read rows 0..N-1, so every task ends up reading the whole file
 * and the scan becomes O(partitions x file size). Byte ranges are computed from the
 * file length alone, and each task reads only its own slice.
 *
 * The boundary rule is the one every splittable-text reader uses: a task starts at
 * its offset, skips to the end of the current line (because that line belongs to the
 * previous task), and reads until it passes its end offset (finishing whatever line
 * straddles the boundary). Every line is therefore read exactly once by exactly one
 * task.
 */
package com.example.dsv2lab.v2;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Serializable;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

import org.apache.spark.sql.types.DataTypes;
import org.apache.spark.sql.types.Metadata;
import org.apache.spark.sql.types.StructField;
import org.apache.spark.sql.types.StructType;
import org.apache.spark.sql.util.CaseInsensitiveStringMap;

public final class CsvFile implements Serializable {

  private static final long serialVersionUID = 1L;

  private final String path;
  private final int targetPartitions;

  private CsvFile(String path, int targetPartitions) {
    this.path = path;
    this.targetPartitions = targetPartitions;
  }

  public static CsvFile from(CaseInsensitiveStringMap options) {
    String path = options.get("path");
    if (path == null) {
      throw new IllegalArgumentException(
          "CsvV2Source requires a 'path' option, for example .option(\"path\", \"/tmp/people.csv\")");
    }
    int partitions = options.getInt("partitions", 2);
    if (partitions < 1) {
      throw new IllegalArgumentException("'partitions' must be at least 1, got " + partitions);
    }
    return new CsvFile(path, partitions);
  }

  public String path() {
    return path;
  }

  /**
   * Reads only the first line to derive an all-string schema.
   *
   * Note what this does NOT do: read the file. Schema inference on the driver is
   * called during planning, so making it proportional to file size is a common way
   * to make large-table planning slow.
   */
  public StructType schema() {
    List<String> header = splitLine(headerLine());
    StructField[] fields = new StructField[header.size()];
    for (int i = 0; i < header.size(); i++) {
      fields[i] = new StructField(header.get(i), DataTypes.StringType, true, Metadata.empty());
    }
    return new StructType(fields);
  }

  /** The raw header line, or an empty string for an empty file. */
  String headerLine() {
    Path p = requireFile();
    try (BufferedReader r = Files.newBufferedReader(p, StandardCharsets.UTF_8)) {
      String first = r.readLine();
      return first == null ? "" : first;
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
  }

  /** Byte length of the header line including its newline, which data ranges start after. */
  long headerLength() {
    String header = headerLine();
    if (header.isEmpty()) {
      return 0L;
    }
    // +1 for the newline. A file with CRLF endings would need +2; kept simple here
    // because the boundary logic tolerates being a byte early, it just skips a line.
    return header.getBytes(StandardCharsets.UTF_8).length + 1L;
  }

  /**
   * Splits the data region into contiguous byte ranges, one per target partition.
   *
   * Computed from the file length only. No data is read, so planning cost does not
   * grow with the file.
   */
  public List<long[]> byteRanges() {
    Path p = requireFile();
    long size;
    try {
      size = Files.size(p);
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }

    long dataStart = headerLength();
    long dataLength = Math.max(0L, size - dataStart);

    List<long[]> ranges = new ArrayList<>();
    if (dataLength == 0L) {
      ranges.add(new long[] {dataStart, dataStart});
      return ranges;
    }

    long per = (long) Math.ceil((double) dataLength / targetPartitions);
    for (long start = dataStart; start < size; start += per) {
      ranges.add(new long[] {start, Math.min(start + per, size)});
    }
    return ranges;
  }

  /**
   * Opens a reader positioned for one byte range, yielding that range's lines and
   * nothing else. Rows are produced lazily: this never holds the file in memory.
   */
  public LineRange open(long start, long end) {
    return new LineRange(requireFile(), start, end, headerLength());
  }

  private Path requireFile() {
    Path p = Paths.get(path);
    if (!Files.exists(p)) {
      throw new UncheckedIOException(new IOException("No such CSV file: " + path));
    }
    return p;
  }

  public static List<String> splitLine(String line) {
    List<String> out = new ArrayList<>();
    if (line.isEmpty()) {
      return out;
    }
    for (String cell : line.split(",", -1)) {
      out.add(cell.trim());
    }
    return out;
  }

  /**
   * A lazy line iterator over one byte range, implementing the split boundary rule.
   *
   * Not an Iterator by design: DSV2's PartitionReader is a next()/get() cursor, so
   * this exposes the same shape and the reader becomes a thin delegation.
   */
  public static final class LineRange implements AutoCloseable {

    private final java.io.InputStream in;
    private final BufferedReader reader;
    private final long end;
    private long position;
    private String current;

    LineRange(Path file, long start, long end, long dataStart) {
      this.end = end;
      try {
        // Seek to start - 1, not start. This is the trick that makes the boundary
        // rule correct, and it is what Hadoop's LineRecordReader does.
        //
        // The naive version ("if start > dataStart, discard one line") loses rows: a
        // range beginning exactly on a line boundary discards a whole record that no
        // other range will read. You cannot tell from the offset alone whether you
        // landed mid-line or on a boundary.
        //
        // Backing up one byte resolves it without a special case. Discarding one line
        // from start-1 either consumes the tail of a straddling line, or, when
        // start-1 is itself the newline, consumes only that newline and leaves the
        // cursor exactly at start. Both cases end up correct.
        long seek = start > dataStart ? start - 1 : start;
        this.in = Files.newInputStream(file);
        long skipped = 0;
        while (skipped < seek) {
          long n = in.skip(seek - skipped);
          if (n <= 0) {
            break;
          }
          skipped += n;
        }
        this.position = skipped;
        this.reader = new BufferedReader(new java.io.InputStreamReader(in, StandardCharsets.UTF_8));

        if (start > dataStart) {
          String discarded = reader.readLine();
          if (discarded != null) {
            position += discarded.getBytes(StandardCharsets.UTF_8).length + 1L;
          }
        }
      } catch (IOException e) {
        throw new UncheckedIOException(e);
      }
    }

    /**
     * Advances to the next line in range. Reads past the end offset only far enough
     * to finish a line that straddles the boundary, which is what guarantees every
     * line is read exactly once across all ranges.
     */
    public boolean next() {
      if (position >= end) {
        current = null;
        return false;
      }
      try {
        String line = reader.readLine();
        if (line == null) {
          current = null;
          return false;
        }
        position += line.getBytes(StandardCharsets.UTF_8).length + 1L;
        if (line.isBlank()) {
          return next();
        }
        current = line;
        return true;
      } catch (IOException e) {
        throw new UncheckedIOException(e);
      }
    }

    public String get() {
      return current;
    }

    @Override
    public void close() {
      try {
        reader.close();
        in.close();
      } catch (IOException e) {
        // Best effort on close.
      }
    }
  }
}
