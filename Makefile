
SHELL = /bin/zsh

.PHONY: all test clean

test:
	source ./env.sh && \
	python3 -m unittest test.simple_test
