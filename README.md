# transformation
Django app to transform input sources to RDF


## Installation
* Clone the repository into your existing Django project:
```shell
  git clone https://github.com/LinDA-tools/transformation.git
```
* Import the app settings.py file into your project settings.py:
```shell
  from transformation.config.settings import *
```
* Add the app url patterns to your project urls.py:
```shell
  url(r'^transformation/', include('transformation.urls'))
```
* Install MySQL database connector for Python 3 (https://github.com/PyMySQL/mysqlclient-python)
```shell
  sudo apt-get install python3-dev libmysqlclient-dev
  pip install mysqlclient
```
* Add the app requirements.txt to your project requirements.txt:
```shell
  transformation/requirements.txt
```
