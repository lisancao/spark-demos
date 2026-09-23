/* Shared file I/O for the V1 example. Not part of the DSV1 or DSV2 API. */
package com.example.dsv2lab.v1;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

final class V1CsvIo {

  private V1CsvIo() {}

  static List<String> allLines(String path) {
    Path p = Paths.get(path);
    if (!Files.exists(p)) {
      throw new UncheckedIOException(new IOException("No such CSV file: " + path));
    }
    try {
      List<String> out = new ArrayList<>();
      for (String line : Files.readAllLines(p, StandardCharsets.UTF_8)) {
        if (!line.isBlank()) {
          out.add(line);
        }
      }
      return out;
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
  }

  static List<String> header(String path) {
    List<String> all = allLines(path);
    return all.isEmpty() ? List.of() : split(all.get(0));
  }

  static List<String> dataLines(String path) {
    List<String> all = allLines(path);
    return all.isEmpty() ? List.of() : all.subList(1, all.size());
  }

  static List<String> split(String line) {
    List<String> out = new ArrayList<>();
    for (String cell : line.split(",", -1)) {
      out.add(cell.trim());
    }
    return out;
  }

  static void write(String path, String[] header, List<String> dataLines) {
    List<String> out = new ArrayList<>();
    out.add(String.join(",", header));
    out.addAll(dataLines);
    try {
      Files.write(Paths.get(path), out, StandardCharsets.UTF_8);
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
  }
}
