const hre=require('hardhat');
async function main(){const F=await hre.ethers.getContractFactory('FindChain');const f=await F.deploy();await f.waitForDeployment();console.log('FindChain deployed:',await f.getAddress());}
main().catch(e=>{console.error(e);process.exitCode=1;});
