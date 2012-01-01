all:
	@echo "To install astat in ~/bin, run 'make install'." >&2
	@exit 1

install:
	cp astat.py $$HOME/bin/astat
	chmod 755 $$HOME/bin/astat
