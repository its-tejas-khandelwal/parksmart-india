(function(){ setInterval(function(){ fetch('/health').catch(function(){}); }, 600000); })(); 
