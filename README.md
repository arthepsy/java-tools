# java-tools
Java tools (e.g, jdk &amp; maven environment setup)

* `java.get.py` -- download JDK/Maven  
  ```
  ./java.get.py jdk `uname -m` 8
  Available JDK8 versions: 25, 20, 11, 5, 0
  ```

* `java.env.sh` -- set JDK/Maven environemnt  
  ```
  source java.env.sh mvn /opt/apache-maven-3.2.5 "-Xss2m"
  ```
  
