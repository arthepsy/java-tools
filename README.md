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

  ```
  ./java.class_name.sh misc.class
  misc.class: com.example.code.Domain$Trait$FieldHelper
  ```

* `jetty.obf.py` -- string (de)obfuscator from Jetty

  ```
  ./jetty.obf.py password
  OBF:1v2j1uum1xtv1zej1zer1xtn1uvk1v1v
  ```
  ```
  ./jetty.obf.py OBF:1v2j1uum1xtv1zej1zer1xtn1uvk1v1v
  password
  ```

* `ar.mvn.py` -- Maven project analyzer  

