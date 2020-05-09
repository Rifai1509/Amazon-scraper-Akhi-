How to run.

0. Edit params.json
0. Install requirements
```shell script
pip install -r .\requirements.txt
```

1. Collecting all product links every page
```shell script
py .\1_get_all_links.py
```

2. Get detail every product
```shell script
py .\2_get_detail.py
```

3. Create excel
```shell script
py .\3_create_excel.py
```