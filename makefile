test:
	py.test -v  psims --cov=psims --cov-report=html

retest:
	py.test -v psims --lf