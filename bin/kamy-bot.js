#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),path=require("node:path"),os=require("node:os"),crypto=require("node:crypto"),http=require("node:http");
const {spawn,spawnSync}=require("node:child_process");
const VERSION="1.3.0",PACKAGE_ROOT=path.resolve(__dirname,"..");
const INSTALL_ROOT=path.resolve(process.env.KAMY_HOME||path.join(os.homedir(),".kamy-bot")),APP_DIR=path.join(INSTALL_ROOT,"app");
const RUNTIME_FILES=["app.py","extensions.py","security.py","requirements.txt","requirements-browser.txt",".env.example","Dockerfile","docker-compose.yml","static","assets"];
function help(){console.log("Kamy Bot "+VERSION+" — floating local AI companion\n\nUsage:\n  npm exec --yes --package=./Kamy-Bot -- kamy-bot              Install/update and open the floating desktop island\n  npm exec --yes --package=./Kamy-Bot -- kamy-bot --web         Open the local interface in a browser\n  npm exec --yes --package=./Kamy-Bot -- kamy-bot --docker     Start with Docker and isolated Chromium\n  npm exec --yes --package=./Kamy-Bot -- kamy-bot --no-open    Start without opening a window\n  npm exec --yes --package=./Kamy-Bot -- kamy-bot --port 9000  Use a different localhost port\n  npm exec --yes --package=./Kamy-Bot -- kamy-bot --setup-only  Prepare .venv and install dependencies\n  npm exec --yes --package=./Kamy-Bot -- kamy-bot --help       Show this help\n\nThe default desktop mode uses Electron when available. Without Electron (including Termux), the launcher opens the local browser.\nRequirements: Node.js 18+ and Python 3.11+. Docker is required only for --docker.\nLocal files: "+INSTALL_ROOT+"\n")}
function parseEnv(content){const values={};for(const line of content.split(/\r?\n/)){const match=line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);if(!match||match[1].startsWith("#"))continue;let value=match[2];if((value.startsWith('"')&&value.endsWith('"'))||(value.startsWith("'")&&value.endsWith("'")))value=value.slice(1,-1);values[match[1]]=value}return values}
function loadLocalEnv(content){for(const [key,value] of Object.entries(parseEnv(content)))if(process.env[key]===undefined||String(process.env[key]).trim()==="")process.env[key]=value;process.env.KAMY_DATA_DIR=path.join(APP_DIR,"data")}
function installVenv(python){
 const venvDir=path.join(APP_DIR,".venv");
 const venvPython=process.platform==="win32"?path.join(venvDir,"Scripts","python.exe"):path.join(venvDir,"bin","python");
 const cwd=APP_DIR;
 const validVenv=()=>{const check=spawnSync(venvPython,["-c","import sys; assert sys.prefix != sys.base_prefix; print(sys.executable)"],{encoding:"utf8"});return !check.error&&check.status===0};
 if(!validVenv()){
  if(fs.existsSync(venvDir)){console.log("O .venv existente está incompleto ou inválido; recriando apenas o ambiente virtual...");fs.rmSync(venvDir,{recursive:true,force:true})}
  console.log("Criando ambiente virtual Python em "+venvDir);
  run(python.command,[...python.prefix,"-m","venv",venvDir],{cwd});
 }
 if(!validVenv())throw new Error("Não foi possível iniciar o Python dentro de .venv. Reinstale Python 3.11+ com suporte a venv/ensurepip.");
 const pipCheck=spawnSync(venvPython,["-m","pip","--version"],{encoding:"utf8"});
 if(pipCheck.error||pipCheck.status!==0)run(venvPython,["-m","ensurepip","--upgrade"],{cwd});
 const requirementsPath=path.join(APP_DIR,"requirements.txt");
 const digest=crypto.createHash("sha256").update(fs.readFileSync(requirementsPath)).digest("hex");
 const marker=path.join(venvDir,".kamy-requirements-sha256");
 const markerMatches=fs.existsSync(marker)&&fs.readFileSync(marker,"utf8").trim()===digest;
 const importsCheck=spawnSync(venvPython,["-c","import fastapi,uvicorn,httpx,pydantic,cryptography,jsonschema,mcp"],{stdio:"ignore"});
 if(!markerMatches||importsCheck.error||importsCheck.status!==0){
  console.log("Instalando requirements.txt usando o Python do .venv...");
  console.log("Interpretador: "+venvPython);
  run(venvPython,["-m","pip","install","--disable-pip-version-check","--upgrade","pip"],{cwd});
  run(venvPython,["-m","pip","install","--disable-pip-version-check","--only-binary=pydantic-core","-r",requirementsPath],{cwd});
  const verify=spawnSync(venvPython,["-c","import fastapi,uvicorn,httpx,pydantic,cryptography,jsonschema,mcp; print('Python environment OK')"],{encoding:"utf8"});
  if(verify.error||verify.status!==0){
   const diagnostic=(verify.stderr||verify.stdout||"sem saída do Python").trim();
   throw new Error("As dependências foram instaladas, mas a validação de imports falhou dentro do .venv.\n"+diagnostic);
  }
  fs.writeFileSync(marker,digest+"\n","utf8");
  console.log("Dependências instaladas e verificadas dentro de .venv.");
 }else{
  console.log("Ambiente .venv e requirements.txt já estão atualizados.");
 }
 process.env.VIRTUAL_ENV=venvDir;
 process.env.PATH=path.dirname(venvPython)+path.delimiter+(process.env.PATH||"");
 console.log("Ambiente virtual ativo: "+venvPython);
 return venvPython;
}
function openBrowser(url){
 let command,args;if(process.platform==="win32"){command="cmd";args=["/c","start","",url]}else if(process.platform==="darwin"){command="open";args=[url]}else if(commandWorks("termux-open-url",["--help"])){command="termux-open-url";args=[url]}else{command="xdg-open";args=[url]}
 const child=spawn(command,args,{stdio:"ignore",detached:true});child.on("error",()=>console.log("Abra manualmente: "+url));child.unref();
}
function findElectronBinary(){
 try{const binary=require("electron");return typeof binary==="string"&&fs.existsSync(binary)?binary:null}catch{return null}
}
function openDesktop(url,serverChild){
 const executable=findElectronBinary();
 const entry=path.join(PACKAGE_ROOT,"desktop","main.js");
 if(!executable||!fs.existsSync(entry)){
  console.log("Electron não está disponível nesta plataforma; abrindo a interface local no navegador.");
  openBrowser(url);return null;
 }
 const child=spawn(executable,[entry,url],{cwd:PACKAGE_ROOT,env:process.env,stdio:"inherit"});
 child.once("error",error=>{
  console.warn("Não foi possível iniciar a janela desktop: "+error.message);
  console.log("Abrindo a interface local no navegador.");
  openBrowser(url);
 });
 child.once("exit",()=>{if(serverChild&&serverChild.exitCode===null)serverChild.kill("SIGINT")});
 return child;
}
function openInterface(url,noOpen,useWeb,serverChild){
 if(noOpen)return null;
 if(useWeb){openBrowser(url);return null}
 return openDesktop(url,serverChild);
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
 const setupOnly=args.includes("--setup-only");
 const dockerMode=args.includes("--docker"),noOpen=args.includes("--no-open"),useWeb=args.includes("--web"),portIndex=args.indexOf("--port");
 copyRuntime();const envContent=prepareEnv(),values=parseEnv(envContent),port=portIndex>=0?Number(args[portIndex+1]):Number(values.KAMY_PORT||8765);
 if(!Number.isInteger(port)||port<1024||port>65535)throw new Error("Porta inválida. Use um valor entre 1024 e 65535.");
 const url="http://127.0.0.1:"+port;
 if(dockerMode){await dockerStart(port);openInterface(url,noOpen,useWeb,null);console.log("Kamy Bot está em execução com Docker: "+url);console.log("Parar: docker compose -f "+path.join(APP_DIR,"docker-compose.yml")+" down");return}
 const python=findPython();loadLocalEnv(envContent);process.env.KAMY_PORT=String(port);const pythonExe=installVenv(python);fs.mkdirSync(path.join(APP_DIR,"data"),{recursive:true});
 if(setupOnly){console.log("Preparação concluída. .venv e requirements.txt estão prontos em "+APP_DIR);return}
 if(await healthCheck(port)){console.log("Kamy Bot já está respondendo em "+url);openInterface(url,noOpen,useWeb,null);return}
 const bind=process.env.KAMY_BIND||"127.0.0.1";
 const child=spawn(pythonExe,["-m","uvicorn","app:app","--host",bind,"--port",String(port)],{cwd:APP_DIR,env:process.env,stdio:"inherit"});
 process.once("SIGINT",()=>child.kill("SIGINT"));process.once("SIGTERM",()=>child.kill("SIGTERM"));
 await waitForServer(child,port);console.log("Kamy Bot pronto: "+url);console.log("Parar o servidor: Ctrl+C");openInterface(url,noOpen,useWeb,child);
 await new Promise((resolve,reject)=>{child.once("exit",code=>code===0?resolve():reject(new Error("Kamy encerrou com código "+code)));child.once("error",reject)});
}
main().catch(error=>{console.error("\nKamy Bot: "+error.message);process.exitCode=1});
