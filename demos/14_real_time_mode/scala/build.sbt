// Step 4 of the Real-time Mode demo: a per-shopper recommender in transformWithState.
// Scala because Real-time Mode runs only the JVM transformWithState (PySpark's is rejected).
ThisBuild / scalaVersion := "2.13.18"
ThisBuild / organization := "net.systemsnull"
ThisBuild / version := "0.1.0"

val sparkVersion = "4.3.0"

lazy val root = (project in file("."))
  .settings(
    name := "bookshop-recs",
    libraryDependencies ++= Seq(
      "org.apache.spark" %% "spark-sql" % sparkVersion % Provided,
      "org.apache.spark" %% "spark-sql-kafka-0-10" % sparkVersion % Provided,
    ),
    scalacOptions ++= Seq("-deprecation", "-feature", "-Xlint:unused"),
  )
