import { NextRequest, NextResponse } from "next/server";
import { exec } from "child_process";
import fs from "fs";
import path from "path";
import { promisify } from "util";
import os from "os";

const execAsync = promisify(exec);


export async function GET() {
    return NextResponse.json({ status: "OCR API is active and ready for POST requests." });
}

export async function POST(req: NextRequest) {
    try {
        const formData = await req.formData();
        const file = formData.get("file") as File;

        if (!file) {
            return NextResponse.json({ error: "No file uploaded" }, { status: 400 });
        }

        // Prepare temp file path
        const tempDir = os.tmpdir();
        const tempFilePath = path.join(tempDir, `${Date.now()}-${file.name}`);

        // Save uploaded file to temp path
        const buffer = Buffer.from(await file.arrayBuffer());
        await fs.promises.writeFile(tempFilePath, buffer);

        // Call Python script (Using the standalone engine script)
        const scriptPath = path.join(process.cwd(), "api/extract.py");

        // Try both "python" and "python3"
        let pythonCmd = "python";
        try {
            await execAsync("python --version");
        } catch {
            pythonCmd = "python3";
        }

        // We use the same script but call it via CLI for local dev support
        const { stdout, stderr } = await execAsync(`${pythonCmd} "${scriptPath}" "${tempFilePath}"`);

        // Clean up
        await fs.promises.unlink(tempFilePath);

        if (stderr && !stdout) {
            console.error("Python Stderr:", stderr);
        }

        try {
            // The script handles both JSON output and printing to stdout
            const results = JSON.parse(stdout);
            return NextResponse.json(results);
        } catch (parseError) {
            console.error("Error parsing Python output:", stdout);
            return NextResponse.json({ error: "Invalid extraction output from engine" }, { status: 500 });
        }

    } catch (error: any) {
        console.error("Main Error:", error);
        return NextResponse.json({ error: error.message || "Extraction Failed" }, { status: 500 });
    }
}
