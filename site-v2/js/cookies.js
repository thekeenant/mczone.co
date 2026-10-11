function createCookie(name,value,days) {
   var date = new Date();
   date.setTime(date.getTime()+(days*24*60*60*1000));
   var expires = date.toGMTString();
   document.cookie = name+"="+value+"; expires="+expires+"; path=/";
}
/** Check if already a cookie has been created. **/
function readCookie(name) {
    var flag = 0;
    var dcmntCookie = document.cookie.split(';');
    for(var i=0;i < dcmntCookie.length;i++) {
        var ck = dcmntCookie[i];
        while (ck.charAt(0)==' ') {
            ck = ck.substring(1,ck.length);
        }
        if(ck) {
            cparts = ck.split('=');
            if (cparts[0] == name) flag=1;
        }              
    }     
    if(flag) { 
        return true; 
    } else {
        return false; 
    }  
}
/** Check if cookie exists else create a new one. **/
function checkCookie(name) {
    if (readCookie(name)) {
        document.getElementById('popup').style.display = "none";
        document.getElementById('popup').style.visibility = "hidden";
    }
    else {
      document.getElementById('popup').style.display = "block";
      document.getElementById('popup').style.visibility = "visible";
      createCookie(name,"cookie 4 the day",1); 
    }
}

function eraseCookie(name) {
  createCookie(name,"",-1);
}