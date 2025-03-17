const poultry=artifacts.require("poultry");

module.exports=function(deployer){
    deployer.deploy(poultry);
}