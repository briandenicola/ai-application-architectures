const fs = require("node:fs");
const path = require("node:path");
const Ajv = require("ajv-draft-04");
const addFormats = require("ajv-formats");

const schema = require(path.join(
  path.dirname(require.resolve("@microsoft/m365agentstoolkit-cli/package.json")),
  "json-schemas/teams/v1.29/MicrosoftTeams.schema.json",
));
const validator = new Ajv({ strict: false, allErrors: true });
addFormats(validator);
const validate = validator.compile(schema);
const manifest = JSON.parse(fs.readFileSync(0, "utf8"));
if (!validate(manifest)) {
  console.error(JSON.stringify(validate.errors, null, 2));
  process.exitCode = 1;
}
