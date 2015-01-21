# java-tools
Java tools (e.g, jdk &amp; maven environment)

* `java.get.py` -- download JDK/Maven  
  ```
  ./java.get.py jdk `uname -m` 8
  Available JDK8 versions: 25, 20, 11, 5, 0
  ```

* `java.env.sh` -- set JDK/Maven environemnt  
  ```
  source java.env.sh mvn /opt/apache-maven-3.2.5 "-Xss2m"
  ```

* `java.class_name.sh` -- get fully qualified class name from .class file  

  Requires [BCEL](http://commons.apache.org/proper/commons-bcel/). download and move it to `lib/bcel-5.2.jar`  
  ```
  ./java.class_name.sh misc.class
  misc.class: com.example.code.Domain$Trait$FieldHelper
  ```
