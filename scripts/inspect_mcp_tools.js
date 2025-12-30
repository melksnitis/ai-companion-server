#!/usr/bin/env node

const { spawn } = require('child_process');

const serverCommand = process.argv[2] || 'npx';
const serverArgs = process.argv.slice(3);

if (serverArgs.length === 0) {
  console.error('Usage: node inspect_mcp_tools.js npx @cocal/google-calendar-mcp');
  process.exit(1);
}

console.log(`Inspecting MCP server: ${serverCommand} ${serverArgs.join(' ')}`);

const mcp = spawn(serverCommand, serverArgs, {
  env: process.env,
  cwd: process.cwd()
});

let buffer = '';
mcp.stdout.on('data', (data) => {
  buffer += data.toString();
  const lines = buffer.split('\n');
  buffer = lines.pop();
  
  lines.forEach(line => {
    if (line.trim()) {
      try {
        const msg = JSON.parse(line);
        if (msg.result && msg.result.tools) {
          console.log('\n=== AVAILABLE MCP TOOLS ===\n');
          msg.result.tools.forEach(tool => {
            console.log(`Tool: ${tool.name}`);
            if (tool.description) {
              console.log(`  Description: ${tool.description}`);
            }
          });
          console.log('\n');
          mcp.kill();
          process.exit(0);
        }
      } catch (e) {}
    }
  });
});

mcp.stderr.on('data', (data) => {
  console.error('Server stderr:', data.toString());
});

setTimeout(() => {
  const initRequest = JSON.stringify({
    jsonrpc: '2.0',
    id: 1,
    method: 'initialize',
    params: {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'tool-inspector', version: '1.0.0' }
    }
  }) + '\n';
  
  mcp.stdin.write(initRequest);
  
  setTimeout(() => {
    const listToolsRequest = JSON.stringify({
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/list',
      params: {}
    }) + '\n';
    
    mcp.stdin.write(listToolsRequest);
  }, 1000);
}, 1000);

setTimeout(() => {
  console.log('Timeout - no tools found or server did not respond');
  mcp.kill();
  process.exit(1);
}, 10000);
