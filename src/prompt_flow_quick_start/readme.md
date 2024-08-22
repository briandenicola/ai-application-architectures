# Documentation

# Cli
```python
pip install promptflow
pf connection create --file connections/azure_openai.yml --set api_key=<your_api_key> api_base=<your_api_base> --name open_ai_connection
pf flow test --flow flow:chat --inputs question="What's the capital of France?"
```

# Python
```python
python ./flow.py
```