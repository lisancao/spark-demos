/*
 * The capability DSV1 structurally cannot have: a catalog.
 *
 * Registered with:
 *   spark.sql.catalog.demo = com.example.dsv2lab.catalog.CsvCatalog
 *   spark.sql.catalog.demo.warehouse = /tmp/dsv2lab/warehouse
 *
 * After that, `demo.<namespace>.<table>` resolves through this class, and SQL DDL
 * works: CREATE TABLE, DROP TABLE, SHOW TABLES, SHOW NAMESPACES.
 *
 * Note which interfaces do the work:
 *   CatalogPlugin       -> initialize(name, options), the registration hook
 *   TableCatalog        -> the table lifecycle
 *   SupportsNamespaces  -> namespace listing and DDL, including multi-part names
 *
 * Every property under spark.sql.catalog.<name>. arrives in initialize as options,
 * which is how a catalog gets its own configuration.
 */
package com.example.dsv2lab.catalog;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import org.apache.spark.sql.catalyst.analysis.NamespaceAlreadyExistsException;
import org.apache.spark.sql.catalyst.analysis.NoSuchNamespaceException;
import org.apache.spark.sql.catalyst.analysis.NoSuchTableException;
import org.apache.spark.sql.catalyst.analysis.TableAlreadyExistsException;
import org.apache.spark.sql.connector.catalog.Column;
import org.apache.spark.sql.connector.catalog.Identifier;
import org.apache.spark.sql.connector.catalog.NamespaceChange;
import org.apache.spark.sql.connector.catalog.SupportsNamespaces;
import org.apache.spark.sql.connector.catalog.Table;
import org.apache.spark.sql.connector.catalog.TableCatalog;
import org.apache.spark.sql.connector.catalog.TableChange;
import org.apache.spark.sql.connector.catalog.TableInfo;
import org.apache.spark.sql.connector.expressions.Transform;
import org.apache.spark.sql.types.StructType;
import org.apache.spark.sql.util.CaseInsensitiveStringMap;

public class CsvCatalog implements TableCatalog, SupportsNamespaces {

  private String name;
  private Path warehouse;

  /** Called once at registration. Options are the spark.sql.catalog.<name>.* keys. */
  @Override
  public void initialize(String name, CaseInsensitiveStringMap options) {
    this.name = name;
    String dir = options.get("warehouse");
    if (dir == null) {
      throw new IllegalArgumentException(
          "CsvCatalog needs spark.sql.catalog." + name + ".warehouse set to a directory");
    }
    this.warehouse = Paths.get(dir);
    try {
      Files.createDirectories(warehouse);
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
  }

  @Override
  public String name() {
    return name;
  }

  // ---------- TableCatalog ----------

  @Override
  public Identifier[] listTables(String[] namespace) throws NoSuchNamespaceException {
    Path dir = namespaceDir(namespace);
    if (!Files.isDirectory(dir)) {
      throw new NoSuchNamespaceException(namespace);
    }
    List<Identifier> out = new ArrayList<>();
    try (Stream<Path> files = Files.list(dir)) {
      files.filter(p -> p.getFileName().toString().endsWith(".csv"))
          .forEach(p -> {
            String fn = p.getFileName().toString();
            out.add(Identifier.of(namespace, fn.substring(0, fn.length() - 4)));
          });
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
    return out.toArray(new Identifier[0]);
  }

  @Override
  public Table loadTable(Identifier ident) throws NoSuchTableException {
    Path f = tableFile(ident);
    if (!Files.exists(f)) {
      throw new NoSuchTableException(ident);
    }
    return CsvCatalogTable.load(ident, f);
  }

  /**
   * CREATE TABLE, current signature.
   *
   * This method has been rewritten twice, which is worth knowing if you are
   * following an older tutorial. All three overloads still exist:
   *   createTable(Identifier, StructType, Transform[], Map)  deprecated in 3.4.0
   *   createTable(Identifier, Column[],   Transform[], Map)  deprecated in 4.1.0
   *   createTable(Identifier, TableInfo)                     current, since 4.1.0
   *
   * TableInfo bundles columns, partitions, properties, and constraints into one
   * argument, so future additions do not require another overload. Implement this
   * one; the deprecated pair have default implementations that Spark routes here.
   */
  @Override
  public Table createTable(Identifier ident, TableInfo info) throws TableAlreadyExistsException {
    Path f = tableFile(ident);
    if (Files.exists(f)) {
      throw new TableAlreadyExistsException(ident);
    }
    try {
      Files.createDirectories(f.getParent());
      List<String> header = new ArrayList<>();
      for (Column c : info.columns()) {
        header.add(c.name());
      }
      Files.write(f, List.of(String.join(",", header)));
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
    return CsvCatalogTable.load(ident, f);
  }

  @Override
  public Table alterTable(Identifier ident, TableChange... changes) throws NoSuchTableException {
    // Deliberately unsupported. Throwing a clear error beats a partial
    // implementation that silently drops a requested change.
    throw new UnsupportedOperationException(
        "CsvCatalog does not support ALTER TABLE. Supported: CREATE, DROP, RENAME, SELECT, INSERT.");
  }

  @Override
  public boolean dropTable(Identifier ident) {
    try {
      return Files.deleteIfExists(tableFile(ident));
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
  }

  @Override
  public void renameTable(Identifier from, Identifier to)
      throws NoSuchTableException, TableAlreadyExistsException {
    Path src = tableFile(from);
    Path dst = tableFile(to);
    if (!Files.exists(src)) {
      throw new NoSuchTableException(from);
    }
    if (Files.exists(dst)) {
      throw new TableAlreadyExistsException(to);
    }
    try {
      Files.createDirectories(dst.getParent());
      Files.move(src, dst);
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
  }

  // ---------- SupportsNamespaces ----------

  /**
   * Multi-part namespaces are the thing the Hive Metastore could not express. Here
   * a namespace maps to a nested directory, so demo.a.b.tbl works with an arbitrary
   * number of levels.
   */
  @Override
  public String[][] listNamespaces() {
    return listNamespaces(new String[0]);
  }

  @Override
  public String[][] listNamespaces(String[] namespace) {
    Path dir = namespaceDir(namespace);
    List<String[]> out = new ArrayList<>();
    if (!Files.isDirectory(dir)) {
      return new String[0][];
    }
    try (Stream<Path> paths = Files.list(dir)) {
      paths.filter(Files::isDirectory).forEach(p -> {
        String[] child = new String[namespace.length + 1];
        System.arraycopy(namespace, 0, child, 0, namespace.length);
        child[namespace.length] = p.getFileName().toString();
        out.add(child);
      });
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
    return out.toArray(new String[0][]);
  }

  @Override
  public Map<String, String> loadNamespaceMetadata(String[] namespace) throws NoSuchNamespaceException {
    if (!Files.isDirectory(namespaceDir(namespace))) {
      throw new NoSuchNamespaceException(namespace);
    }
    Map<String, String> meta = new HashMap<>();
    meta.put("location", namespaceDir(namespace).toString());
    return meta;
  }

  @Override
  public void createNamespace(String[] namespace, Map<String, String> metadata)
      throws NamespaceAlreadyExistsException {
    Path dir = namespaceDir(namespace);
    if (Files.isDirectory(dir)) {
      throw new NamespaceAlreadyExistsException(namespace);
    }
    try {
      Files.createDirectories(dir);
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
  }

  @Override
  public void alterNamespace(String[] namespace, NamespaceChange... changes) {
    throw new UnsupportedOperationException("CsvCatalog does not support ALTER NAMESPACE.");
  }

  @Override
  public boolean dropNamespace(String[] namespace, boolean cascade) throws NoSuchNamespaceException {
    Path dir = namespaceDir(namespace);
    if (!Files.isDirectory(dir)) {
      throw new NoSuchNamespaceException(namespace);
    }
    try {
      if (cascade) {
        try (Stream<Path> walk = Files.walk(dir)) {
          walk.sorted((a, b) -> b.getNameCount() - a.getNameCount()).forEach(p -> {
            try {
              Files.deleteIfExists(p);
            } catch (IOException e) {
              throw new UncheckedIOException(e);
            }
          });
        }
        return true;
      }
      return Files.deleteIfExists(dir);
    } catch (IOException e) {
      throw new UncheckedIOException(e);
    }
  }

  // ---------- helpers ----------

  private Path namespaceDir(String[] namespace) {
    Path p = warehouse;
    for (String part : namespace) {
      p = p.resolve(part);
    }
    return p;
  }

  private Path tableFile(Identifier ident) {
    return namespaceDir(ident.namespace()).resolve(ident.name() + ".csv");
  }

  static StructType schemaOf(Column[] columns) {
    StructType s = new StructType();
    for (Column c : columns) {
      s = s.add(c.name(), c.dataType(), c.nullable());
    }
    return s;
  }
}
