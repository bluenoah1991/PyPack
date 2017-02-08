from setuptools import setup, find_packages

setup(
	name = 'pypack2',
	version = '0.1.2',
	author = 'CodeMeow5',
	author_email = 'codemeow@yahoo.com',
	description = 'Python HttpPack server-side plugin based on gevent',
	license = 'MIT',
	keywords = 'httppack',
	url = 'https://github.com/codemeow5/PyPack',
	packages = find_packages(),
	install_requires = ['gevent', 'redis']
)