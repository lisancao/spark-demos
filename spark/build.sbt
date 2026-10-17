// Night City stateful streaming demo, Spark 4.3.0 (rc2 staging artifacts until the release lands on Central).
ThisBuild / scalaVersion := "2.13.18"
ThisBuild / organization := "net.systemsnull"
ThisBuild / version := "0.1.0"

val sparkVersion = sys.props.getOrElse("spark.version", "4.3.0")

lazy val root = (project in file("."))
  .settings(
    name := "nightcity",
    resolvers += "Apache Spark staging (4.3.0-rc2)" at
      "https://repository.apache.org/content/repositories/orgapachespark-1538/",
    libraryDependencies ++= Seq(
      "org.apache.spark" %% "spark-sql" % sparkVersion % Provided,
      "org.apache.spark" %% "spark-sql-kafka-0-10" % sparkVersion % Provided,
      // TwsTester (new in 4.3) ships in spark-sql itself; tests only need scalatest
      "org.scalatest" %% "scalatest" % "3.2.19" % Test,
    ),
    scalacOptions ++= Seq("-deprecation", "-feature", "-Xlint:unused"),
    Test / fork := true,
    Test / javaOptions ++= Seq(
      "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED",
      "--add-opens=java.base/java.nio=ALL-UNNAMED",
      "--add-opens=java.base/java.lang=ALL-UNNAMED",
      "--add-opens=java.base/java.util=ALL-UNNAMED",
      "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED",
      "--add-opens=java.base/sun.security.action=ALL-UNNAMED",
    ),
  )
