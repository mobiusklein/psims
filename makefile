test:
	py.test -v -s psims --cov=psims --cov-report=html --cov-report term

retest:
	py.test -v psims --lf


update-docs:
	git checkout gh-pages
	git pull origin master
	cd docs && make clean html
	git add docs/build/html -f
	git commit -m "update docs"
	git push origin gh-pages
	git checkout master