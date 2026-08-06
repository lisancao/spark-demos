/*
 * Step 5: the write path and its two-phase commit.
 *
 * This is the part of DSV2 a connector gets for free and should not reinvent.
 * Spark runs the protocol:
 *
 *   driver:   createBatchWriterFactory()
 *   executor: DataWriter.write(row) per row, then commit() -> WriterCommitMessage
 *             or abort() if the task fails
 *   driver:   commit(messages[]) if all tasks succeeded, else abort(messages[])
 *
 * The connector's job is to make its own commit atomic. Here each task streams to its
 * own part file and returns that path, then the driver concatenates the parts and does
 * one atomic move. That is the same staging shape real connectors use.
 *
 * Two properties are worth copying, because both are easy to get wrong:
 *
 *   1. The DataWriter streams rows to disk instead of buffering them. A task owns one
 *      partition, which in production can be millions of rows, so a List field means
 *      an OutOfMemoryError on real data.
 *   2. A WriterCommitMessage carries a PATH, not the rows. Commit messages are
 *      collected on the driver, so putting data in them puts the whole dataset in
 *      driver memory. It passes every small test and fails on a real table.
 *
 * Honest limitation of this example: the part files are local temp files, which works
 * here because the driver and executors share a filesystem (local, local-cluster, or a
 * cluster with a shared mount). A production connector writes parts to the target
 * storage system instead, for example object storage, so the driver can reach them
 * from anywhere. The protocol shape does not change, only where the parts live.
 */
package com.example.dsv2lab.v2;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;

import org.apache.spark.sql.catalyst.InternalRow;
import org.apache.spark.sql.connector.write.BatchWrite;
import org.apache.spark.sql.connector.write.DataWriter;
import org.apache.spark.sql.connector.write.DataWriterFactory;
import org.apache.spark.sql.connector.write.LogicalWriteInfo;
import org.apache.spark.sql.connector.write.PhysicalWriteInfo;
import org.apache.spark.sql.connector.write.SupportsTruncate;
import org.apache.spark.sql.connector.write.Write;
import org.apache.spark.sql.connector.write.WriteBuilder;
import org.apache.spark.sql.connector.write.WriterCommitMessage;
import org.apache.spark.sql.types.StructType;

public class CsvWriteBuilder implements WriteBuilder, SupportsTruncate {

  private final StructType schema;
  private final CsvFile file;
  private boolean truncate = false;

  public CsvWriteBuilder(StructType schema, CsvFile file) {
    this.schema = schema;
    this.file = file;
  }

  /**
   * Declaring SupportsTruncate is what makes SaveMode.Overwrite work. Spark calls
   * this instead of failing, and the builder records the intent for commit time.
   */
  @Override
  public WriteBuilder truncate() {
    this.truncate = true;
    return this;
  }

  @Override
  public Write build() {
    return new Write() {
      @Override
      public BatchWrite toBatch() {
        return new CsvBatchWrite(schema, file, truncate);
      }
    };
  }

  /** Coordinates the commit on the driver. */
  static final class CsvBatchWrite implements BatchWrite {

    private final StructType schema;
    private final CsvFile file;
    private final boolean truncate;

    CsvBatchWrite(StructType schema, CsvFile file, boolean truncate) {
      this.schema = schema;
      this.file = file;
      this.truncate = truncate;
    }

    @Override
    public DataWriterFactory createBatchWriterFactory(PhysicalWriteInfo info) {
      return new CsvDataWriterFactory(schema, file.path());
    }

    /**
     * All tasks succeeded. Concatenate the part files each task wrote, then move the
     * result into place, so a reader never observes a half-written file.
     *
     * Note what the commit messages carry: a path per task, not the rows. Rows never
     * pass through the driver, which is the property that lets this scale. A writer
     * that returns its data in the commit message works fine in a demo and then puts
     * the whole dataset in driver memory in production.
     */
    @Override
    public void commit(WriterCommitMessage[] messages) {
      try {
        Path dest = Paths.get(file.path());
        Path staged = Files.createTempFile("csvv2-commit-", ".csv");

        try (BufferedWriter out = Files.newBufferedWriter(staged, StandardCharsets.UTF_8)) {
          if (!truncate && Files.exists(dest)) {
            try (Stream<String> existing = Files.lines(dest, StandardCharsets.UTF_8)) {
              for (String line : (Iterable<String>) existing::iterator) {
                out.write(line);
                out.newLine();
              }
            }
          } else {
            out.write(String.join(",", schema.fieldNames()));
            out.newLine();
          }
          for (WriterCommitMessage m : messages) {
            Path part = Paths.get(((CsvCommitMessage) m).partFile);
            try (Stream<String> rows = Files.lines(part, StandardCharsets.UTF_8)) {
              for (String line : (Iterable<String>) rows::iterator) {
                out.write(line);
                out.newLine();
              }
            }
            Files.deleteIfExists(part);
          }
        }
        Files.move(staged, dest, StandardCopyOption.REPLACE_EXISTING);
      } catch (IOException e) {
        throw new UncheckedIOException(e);
      }
    }

    /**
     * A task failed. Delete the part files that did succeed. Nothing was moved into
     * the destination, so there is no partial state to roll back, which is the point
     * of staging.
     */
    @Override
    public void abort(WriterCommitMessage[] messages) {
      for (WriterCommitMessage m : messages) {
        if (m == null) {
          continue;   // that task never committed
        }
        try {
          Files.deleteIfExists(Paths.get(((CsvCommitMessage) m).partFile));
        } catch (IOException e) {
          // Best effort: abort must not throw and mask the original failure.
        }
      }
    }
  }

  /** Carries a path, not data. Commit messages are collected on the driver. */
  static final class CsvCommitMessage implements WriterCommitMessage {
    private static final long serialVersionUID = 1L;
    final String partFile;

    CsvCommitMessage(String partFile) {
      this.partFile = partFile;
    }
  }

  static final class CsvDataWriterFactory implements DataWriterFactory {
    private static final long serialVersionUID = 1L;
    private final StructType schema;
    private final String path;

    CsvDataWriterFactory(StructType schema, String path) {
      this.schema = schema;
      this.path = path;
    }

    @Override
    public DataWriter<InternalRow> createWriter(int partitionId, long taskId) {
      return new CsvDataWriter(schema, partitionId, taskId);
    }
  }

  /**
   * Per-task writer. Streams rows straight to its own part file and returns that
   * file's path at commit time.
   *
   * Streaming rather than buffering is the point. A task handles one partition, which
   * in production can be millions of rows, so holding them in a List means an
   * out-of-memory error on real data. Nothing here grows with row count.
   */
  static final class CsvDataWriter implements DataWriter<InternalRow> {

    private final StructType schema;
    private final Path partFile;
    private final BufferedWriter out;

    CsvDataWriter(StructType schema, int partitionId, long taskId) {
      this.schema = schema;
      try {
        this.partFile = Files.createTempFile("csvv2-part-" + partitionId + "-" + taskId + "-", ".csv");
        this.out = Files.newBufferedWriter(partFile, StandardCharsets.UTF_8);
      } catch (IOException e) {
        throw new UncheckedIOException(e);
      }
    }

    @Override
    public void write(InternalRow record) {
      String[] cells = new String[schema.fields().length];
      for (int i = 0; i < cells.length; i++) {
        cells[i] = record.isNullAt(i) ? "" : record.getUTF8String(i).toString();
      }
      try {
        out.write(String.join(",", cells));
        out.newLine();
      } catch (IOException e) {
        throw new UncheckedIOException(e);
      }
    }

    @Override
    public WriterCommitMessage commit() {
      try {
        out.flush();
        out.close();
      } catch (IOException e) {
        throw new UncheckedIOException(e);
      }
      return new CsvCommitMessage(partFile.toString());
    }

    /** This task failed. Close the handle and remove the partial part file. */
    @Override
    public void abort() {
      try {
        out.close();
        Files.deleteIfExists(partFile);
      } catch (IOException e) {
        // Best effort: abort must not throw and mask the original failure.
      }
    }

    @Override
    public void close() {
      try {
        out.close();
      } catch (IOException e) {
        // Already closed by commit() in the normal path.
      }
    }
  }
}
