import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const [source, output] = process.argv.slice(2);
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
const result = await presentation.inspect({ kind: "deck,layout,slide,textbox,shape,table,notes", maxChars: 500000 });
await fs.writeFile(output, `${result.ndjson}\n`, "utf8");
console.log(output);
