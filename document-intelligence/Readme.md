General Document	prebuilt-document	https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-layout.pdf
Read	prebuilt-read	https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/rest-api/read.png
Layout	prebuilt-layout	https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/rest-api/layout.png
Health insurance card	prebuilt-healthInsuranceCard.us	https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/rest-api/insurance-card.png
W-2	prebuilt-tax.us.w2	https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/rest-api/w2.png
Invoice	prebuilt-invoice	https://github.com/Azure-Samples/cognitive-services-REST-api-samples/raw/master/curl/form-recognizer/rest-api/invoice.pdf
Receipt	prebuilt-receipt	https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/rest-api/receipt.png
ID document	prebuilt-idDocument	https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/rest-api/identity_documents.png
Business card	prebuilt-businessCard	https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/de5e0d8982ab754823c54de47a47e8e499351523/curl/form-recognizer/rest-api/business_card.jpg

curl -v -i POST "https://cognitive-service-document.internal.lemonstone-cb96d80b.canadacentral.azurecontainerapps.io/formrecognizer/documentModels/prebuilt-document:analyze?api-version=2023-07-31" -H "Content-Type: application/json" --data-ascii "{'urlSource': 'https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-layout.pdf'}"