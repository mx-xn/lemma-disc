val scala3Version  = "3.3.4"
val upickleVersion = "3.3.1"

lazy val commonSettings = Seq(
  scalaVersion := scala3Version
)

lazy val pog = project.in(file("pog"))
  .settings(
    commonSettings,
    libraryDependencies ++= Seq(
      "com.lihaoyi"   %% "upickle"   % upickleVersion,
      "com.lihaoyi"   %% "os-lib"    % "0.10.7",
      "org.scalatest" %% "scalatest" % "3.2.18" % Test
    )
  )

lazy val fragmentation = project.in(file("fragmentation"))
  .settings(
    commonSettings,
    libraryDependencies ++= Seq(
      "com.lihaoyi"   %% "upickle"   % upickleVersion,
      "com.lihaoyi"   %% "os-lib"    % "0.10.7",
      "org.scalatest" %% "scalatest" % "3.2.18" % Test
    ),
    // Pipeline34Test spawns the support Serializer as a subprocess; ensure its
    // classes are compiled before fragmentation/test runs.
    Test / test := (Test / test).dependsOn(support / Compile / compile).value
  )
  .dependsOn(pog)

lazy val support = project.in(file("support"))
  .settings(
    commonSettings,
    libraryDependencies ++= Seq(
      "com.lihaoyi" %% "upickle"    % upickleVersion,
      "org.scalatest" %% "scalatest" % "3.2.18" % Test
    )
  )
