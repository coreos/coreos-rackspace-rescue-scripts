To provision on Rackspace:

* Boot a new Debian cloud server
* Enter rescue mode (Actions > Rescue Mode), note the password
* Wait for host to come up, then run:

  fab -u root -H 1.2.3.4 run_all:http://location/of/coreos.bin.gz

* After that finishes, exit rescue mode
