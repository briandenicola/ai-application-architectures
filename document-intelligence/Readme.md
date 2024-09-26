# Sample Requests

```bash

curl -v -i POST "https://cognitive-service-document.internal.lemonstone-cb96d80b.canadacentral.azurecontainerapps.io/formrecognizer/documentModels/prebuilt-document:analyze?api-version=2022-08-31" -H "Content-Type: application/json" --data-ascii "{'urlSource': 'https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-layout.pdf'}"

curl -v "http://cognitive-service-document.internal.lemonstone-cb96d80b.canadacentral.azurecontainerapps.io/formrecognizer/documentModels/prebuilt-document/analyzeResults/47053a21-4d51-498d-9762-7082686f3931?api-version=2022-08-31"

curl -v -i POST "https://cognitive-service-invoice.internal.lemonstone-cb96d80b.canadacentral.azurecontainerapps.io/formrecognizer/documentModels/prebuilt-invoice:analyze?api-version=2023-07-31" -H "Content-Type: application/json" --data-ascii "{'urlSource': 'https://github.com/Azure-Samples/cognitive-services-REST-api-samples/raw/master/curl/form-recognizer/rest-api/invoice.pdf'}"

curl -v "http://cognitive-service-invoice.internal.lemonstone-cb96d80b.canadacentral.azurecontainerapps.io/formrecognizer/documentModels/prebuilt-invoice/analyzeResults/6e027436-ee30-42ab-b4a3-d264d3be912e?api-version=2023-07-31"

```