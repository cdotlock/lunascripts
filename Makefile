GO ?= go
DIST ?= dist
VERSION ?= dev
GOOS ?= $(shell $(GO) env GOOS)
GOARCH ?= $(shell $(GO) env GOARCH)

.PHONY: build test package clean

build:
	$(GO) build -o bin/lsc ./cmd/lscc

test:
	$(GO) test ./... -v

package: build
	mkdir -p $(DIST)
	LC_ALL=C tar -C bin -czf $(DIST)/lsc-$(VERSION)-$(GOOS)-$(GOARCH).tar.gz lsc

clean:
	rm -rf bin/ $(DIST)/
