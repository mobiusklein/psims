test:
	py.test --log-cli-level DEBUG -v -s psims --cov=psims --cov-report=html --cov-report term

retest:
	py.test -v psims --lf

update-cvs:
	cd psims/controlled_vocabulary/vendor && python update_vendored_cvs.py && python list_cvs.py

cv-versions:
	python scripts/format_cv_versions.py

update-docs:
	git checkout gh-pages
	git pull origin master
	cd docs && make clean html
	git add docs/build/html -f
	git commit -m "update docs"
	git push origin gh-pages
	git checkout master