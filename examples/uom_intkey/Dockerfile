FROM java:8
ADD target/uom_intkey-1.0-SNAPSHOT.jar uom_intkey.jar
# EXPOSE 8080
EXPOSE 4004/tcp
ENTRYPOINT ["java", "-jar", "uom_intkey.jar"]
CMD ["dummy"]
