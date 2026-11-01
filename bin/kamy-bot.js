#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),path=require("node:path"),os=require("node:os"),crypto=require("node:crypto"),http=require("node:http");
const {spawn,spawnSync}=require("node:child_process");
const VERSION="1.2.1",PACKAGE_ROOT=path.resolve(__dirname,"..");
const INSTALL_ROOT=path.resolve(process.env.KAMY_HOME||path.join(os.homedir(),".kamy-bot")),APP_DIR=path.join(INSTALL_ROOT,"app");
const RUNTIME_FILES=["app.py","extensions.py","security.py","requirements.txt","requirements-browser.txt",".env.example","Dockerfile","docker-compose.yml","static","assets"];
function help(){console.log("Kamy Bot "+VERSION+" — local AI companion\n\nUsage:\n  npm exec --yes --package=kamy-bot -- kamy-bot              Install/update and start the native local app\n  npm exec --yes --package=kamy-bot -- kamy-bot --docker     Start with Docker and isolated Chromium browser\n  npm exec --yes --package=kamy-bot -- kamy-bot --no-open    Do not open the browser automatically\n  npm exec --yes --package=kamy-bot -- kamy-bot --port 9000  Use a different localhost port\n  npm exec --yes --package=kamy-bot -- kamy-bot --help       Show this help\n\nRequirements: Node.js 18+ and Python 3.11+.\nDocker Engine/Desktop is required only for --docker.\nLocal files: "+INSTALL_ROOT+"\n")}
function run(command,args,options){const result=spawnSync(command,args,Object.assign({stdio:"inherit"},options||{}));if(result.error)throw result.error;if(result.status!==0)throw new Error("Command failed: "+command+" "+args.join(" "))}
function commandWorks(command,args){const result=spawnSync(command,args||["--version"],{stdio:"ignore"});return !result.error&&result.status===0}
function findPython(){
 const candidates=process.platform==="win32"?[{command:"py",prefix:["-3"]},{command:"python",prefix:[]}]:[{command:"python3",prefix:[]},{command:"python",prefix:[]}];
 for(const candidate of candidates){const check=spawnSync(candidate.command,[...candidate.prefix,"-c","import sys; print('%d.%d' % sys.version_info[:2])"],{encoding:"utf8"});if(check.error||check.status!==0)continue;const parts=(check.stdout||"").trim().split(".").map(Number);if(parts[0]>3||(parts[0]===3&&parts[1]>=11))return candidate}
 throw new Error("Python 3.11+ não foi encontrado. Instale Python e tente novamente.");
}
function copyRuntime(){fs.mkdirSync(APP_DIR,{recursive:true});for(const item of RUNTIME_FILES){const source=path.join(PACKAGE_ROOT,item),destination=path.join(APP_DIR,item);if(!fs.existsSync(source))throw new Error("Arquivo do pacote ausente: "+item);fs.cpSync(source,destination,{recursive:true,force:true})}fs.writeFileSync(path.join(APP_DIR,".kamy-version"),VERSION+"\n","utf8")}
function setEnvValue(content,name,value){const expression=new RegExp("^"+name+"=.*$","m"),line=name+"="+value;return expression.test(content)?content.replace(expression,line):content.replace(/\s*$/,"\n")+line+"\n"}
function prepareEnv(){
 const envPath=path.join(APP_DIR,".env"),samplePath=path.join(APP_DIR,".env.example");
 let content=fs.existsSync(envPath)?fs.readFileSync(envPath,"utf8"):fs.readFileSync(samplePath,"utf8");
 if(!/^KAMY_MASTER_KEY=.+$/m.test(content)){const key=crypto.randomBytes(32).toString("base64").replace(/\+/g,"-").replace(/\//g,"_");content=setEnvValue(content,"KAMY_MASTER_KEY",key);console.log("Chave mestra Fernet criada. Faça backup seguro do arquivo .env.")}
 if(!/^KAMY_PORT=.+$/m.test(content))content=setEnvValue(content,"KAMY_PORT","8765");
 if(!/^KAMY_BIND=.+$/m.test(content))content=setEnvValue(content,"KAMY_BIND","127.0.0.1");
 if(!/^KAMY_BROWSER_ENABLED=.+$/m.test(content))content=setEnvValue(content,"KAMY_BROWSER_ENABLED","0");
 fs.writeFileSync(envPath,content.endsWith("\n")?content:content+"\n",{mode:0o600});try{fs.chmodSync(envPath,0o600)}catch{}return content;
}
function parseEnv(content){const values={};for(const line of content.split(/\r?\n/)){const match=line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);if(!match||match[1].startsWith("#"))continue;let value=match[2];if((value.startsWith('"')&&value.endsWith('"'))||(value.startsWith("'")&&value.endsWith("'")))value=value.slice(1,-1);values[match[1]]=value}return values}
function loadLocalEnv(content){for(const [key,value] of Object.entries(parseEnv(content)))if(process.env[key]===undefined)process.env[key]=value;process.env.KAMY_DATA_DIR=path.join(APP_DIR,"data")}
function installVenv(python){
 const venvPython=process.platform==="win32"?path.join(APP_DIR,".venv","Scripts","python.exe"):path.join(APP_DIR,".venv","bin","python");
 if(!fs.existsSync(venvPython)){console.log("Criando ambiente virtual Python (.venv)...");run(python.command,[...python.prefix,"-m","venv",".venv"],{cwd:APP_DIR})}
 const requirementsPath=path.join(APP_DIR,"requirements.txt"),digest=crypto.createHash("sha256").update(fs.readFileSync(requirementsPath)).digest("hex"),marker=path.join(APP_DIR,".venv",".kamy-requirements-sha256");
 if(!fs.existsSync(marker)||fs.readFileSync(marker,"utf8").trim()!==digest){console.log("Instalando/atualizando requirements.txt no .venv...");run(venvPython,["-m","pip","install","--disable-pip-version-check","--upgrade","pip"],{cwd:APP_DIR});run(venvPython,["-m","pip","install","--disable-pip-version-check","--only-binary=pydantic-core","-r",requirementsPath],{cwd:APP_DIR});fs.writeFileSync(marker,digest+"\n","utf8")}
 return venvPython;
}
function openBrowser(url){
 let command,args;if(process.platform==="win32"){command="cmd";args=["/c","start","",url]}else if(process.platform==="darwin"){command="open";args=[url]}else if(commandWorks("termux-open-url",["--help"])){command="termux-open-url";args=[url]}else{command="xdg-open";args=[url]}
 const child=spawn(command,args,{stdio:"ignore",detached:true});child.on("error",()=>console.log("Abra manualmente: "+url));child.unref();
}
function healthCheck(port){return new Promise(resolve=>{const req=http.get({hostname:"127.0.0.1",port,path:"/api/health",timeout:900},response=>{response.resume();resolve(response.statusCode===200)});req.on("error",()=>resolve(false));req.on("timeout",()=>{req.destroy();resolve(false)})})}
async function waitForServer(child,port){const started=Date.now();while(Date.now()-started<30000){if(child&&child.exitCode!==null)throw new Error("Kamy encerrou antes de ficar pronto. Confira as mensagens acima.");if(await healthCheck(port))return;await new Promise(resolve=>setTimeout(resolve,500))}throw new Error("O servidor não respondeu em 30 segundos. Confira as mensagens do terminal.")}
async function dockerStart(port){
 if(!commandWorks("docker",["compose","version"]))throw new Error("Docker Compose não foi encontrado. Instale/inicie Docker Desktop ou Engine, ou execute sem --docker.");
 const envPath=path.join(APP_DIR,".env");let content=fs.readFileSync(envPath,"utf8");content=setEnvValue(content,"KAMY_BROWSER_ENABLED","1");content=setEnvValue(content,"KAMY_PORT",String(port));fs.writeFileSync(envPath,content,{mode:0o600});
 run("docker",["compose","up","--build","-d"],{cwd:APP_DIR});await waitForServer(null,port);
}
async function main(){
 const args=process.argv.slice(2);if(args.includes("--help")||args.includes("-h"))return help();
 const dockerMode=args.includes("--docker"),noOpen=args.includes("--no-open"),portIndex=args.indexOf("--port");
 copyRuntime();const envContent=prepareEnv(),values=parseEnv(envContent),port=portIndex>=0?Number(args[portIndex+1]):Number(values.KAMY_PORT||8765);
 if(!Number.isInteger(port)||port<1024||port>65535)throw new Error("Porta inválida. Use um valor entre 1024 e 65535.");
 const url="http://127.0.0.1:"+port;
 if(dockerMode){await dockerStart(port);if(!noOpen)openBrowser(url);console.log("Kamy Bot está em execução com Docker: "+url);console.log("Parar: docker compose -f "+path.join(APP_DIR,"docker-compose.yml")+" down");return}
 const python=findPython();loadLocalEnv(envContent);process.env.KAMY_PORT=String(port);const pythonExe=installVenv(python);fs.mkdirSync(path.join(APP_DIR,"data"),{recursive:true});
 if(await healthCheck(port)){console.log("Kamy Bot já está respondendo em "+url);if(!noOpen)openBrowser(url);return}
 const bind=process.env.KAMY_BIND||"127.0.0.1";
 const child=spawn(pythonExe,["-m","uvicorn","app:app","--host",bind,"--port",String(port)],{cwd:APP_DIR,env:process.env,stdio:"inherit"});
 process.once("SIGINT",()=>child.kill("SIGINT"));process.once("SIGTERM",()=>child.kill("SIGTERM"));
 await waitForServer(child,port);console.log("Kamy Bot pronto: "+url);console.log("Parar o servidor: Ctrl+C");if(!noOpen)openBrowser(url);
 await new Promise((resolve,reject)=>{child.once("exit",code=>code===0?resolve():reject(new Error("Kamy encerrou com código "+code)));child.once("error",reject)});
}
main().catch(error=>{console.error("\nKamy Bot: "+error.message);process.exitCode=1});
