# Curl Commands for Testing

```bash
curl -v -i POST "https://cognitive-service-document.internal.lemonstone-cb96d80b.canadacentral.azurecontainerapps.io/formrecognizer/documentModels/prebuilt-document:analyze?api-version=2023-07-31" -H "Content-Type: application/json" --data-ascii "{'urlSource': 'https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-layout.pdf'}"

```