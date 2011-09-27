
include Makeconfig

SUBDIRS = po python scripts

all: build

.PHONY: build
build:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $${dir} || exit; \
	done

.PHONY: clean
clean:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $${dir} clean || exit; \
	done

.PHONY: dist
dist:
	git archive --format=tar --prefix=$(PACKAGE_NAME)-$(PACKAGE_VERSION)/ HEAD | \
		gzip -9 > $(PACKAGE_NAME)-$(PACKAGE_VERSION).tar.gz

.PHONY: install
install:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $${dir} install || exit; \
	done

	-mkdir -pv $(DESTDIR)/usr/lib/pakfire/macros
	cp -vf macros/*.macro $(DESTDIR)/usr/lib/pakfire/macros

	# Install example configuration.
	-mkdir -pv $(DESTDIR)/etc/pakfire.repos.d
	cp -vf examples/pakfire.conf $(DESTDIR)/etc/pakfire.conf
	cp -vf examples/pakfire.repos.d/* $(DESTDIR)/etc/pakfire.repos.d/

.PHONY: check
check:
	./runpychecker.sh
