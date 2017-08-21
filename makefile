test:
	py.test -v  psims --cov=psims --cov-report=html --cov-report term

retest:
	py.test -v psims --lf