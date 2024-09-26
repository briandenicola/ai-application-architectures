# Curl Commands for Testing

```bash
curl -v -i POST "https://cognitive-service-document.internal.lemonstone-cb96d80b.canadacentral.azurecontainerapps.io/formrecognizer/documentModels/prebuilt-document:analyze?api-version=202-07-31" -H "Content-Type: application/json" --data-ascii "{'urlSource': 'https://github.com/briandenicola/openai-learnings/blob/main/document-intelligence/samples/sample-layout.pdf'}"

```