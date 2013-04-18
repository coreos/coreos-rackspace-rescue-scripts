To get going, you need fabric and libcloud installed, and to setup your config.py:

* Install depedencies:

        pip -r requirements.txt

* Setup config.py

        cp dist/config.py .

* Then edit config.py to add your Rackspace API keys and default root password

To provision on Rackspace:

* This should do it all! It will take a few minutes to run.

        fab run_all:hostname,http://location/of/coreos.bin.gz

* Should be booted with that image!

* If booting failed, try this to see what state the node is in:

        fab show_node:hostname

* To delete the node:

        fab destroy_node:hostname

* To test your fabric conductivity (should show uname):

        fab test_node:hostname

