# Path to script
M6S = ../MOM6param_scan.py

TESTS = test1.json test2.json
MD5SUMS = $(TESTS:.json=.md5sum)

all: check

# Put the pamameter file inside a tar file
ball.tar: MOM_parameter_doc.all
	tar zcf $@ $^

# Test JSON dump of a parameter file
test1.json: MOM_parameter_doc.all
	$(M6S) $< > $@

# Test JSON dump of a parameter file from inside a tar file
test2.json: ball.tar
	$(M6S) $< > $@

# Checksum of JSON output
%.md5sum: %.json
	md5sum $< > $@
	
# Check the status of the *.md5sum files which are generated if missing
check: $(MD5SUMS)
	md5sum -c $^

# Remove all files that cannot be regenerated
clean:
	-rm *.json *.tar $(MD5SUMS)
