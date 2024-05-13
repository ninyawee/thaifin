models:
    datamodel-codegen --input stock.json --output stock_model.py
    datamodel-codegen --input list.json --output list_model.py

docs:
    pdoc ./thaifin/ -o ./docs/

