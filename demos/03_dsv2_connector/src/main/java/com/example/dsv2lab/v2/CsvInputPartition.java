/*
 * An InputPartition is a serializable handle describing one independently readable
 * chunk. It travels from the driver to an executor, so it must be Serializable and
 * should stay small: no open file handles, no connections, no schema objects if
 * they can be passed through the factory instead.
 *
 * This one holds two longs. Byte offsets rather than row indexes, because a row
 * index cannot be resolved without reading every earlier row, which would make each
 * task read the whole file.
 *
 * Optionally override preferredLocations() to give Spark data-locality hints. For a
 * distributed filesystem you would return the hosts holding this byte range's blocks.
 */
package com.example.dsv2lab.v2;

import org.apache.spark.sql.connector.read.InputPartition;

public class CsvInputPartition implements InputPartition {

  private static final long serialVersionUID = 1L;

  final long startByte;
  final long endByte;

  public CsvInputPartition(long startByte, long endByte) {
    this.startByte = startByte;
    this.endByte = endByte;
  }

  @Override
  public String toString() {
    return "CsvInputPartition[" + startByte + "," + endByte + ")";
  }
}
