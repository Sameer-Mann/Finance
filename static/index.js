var form,btn,table,inputField,inputElm,mn;
function addAttributes(elm,attributes,values) {
    $(values).each((index,value)=>{
        $(elm).attr(attributes[index],value);
    });
}

function addClasses(obj,values) {
    values.forEach(v=>obj.classList.add(v));
}

function createCopy(elm){
    // var x = document.createElement(elm.tagName);
    // x.innerHTML = elm.innerHTML.trim();
    // return x;
    return $.extend(true,{},elm);
}

function makePostRequest(form11,url){
    return new Promise((resolve,reject)=>{
        var req = new XMLHttpRequest();
        var fd = new FormData(form11[0]),data;
        try{
            req.open("POST",url,true);
        }catch(err){
            console.warn("couldn't complete Request"+err.message);
            reject(err);
        }
        try{
            req.send(fd);
        }catch(err){
            console.warn(err);
        }
        req.onreadystatechange = function() {
            if(this.status==200 && this.readyState == 4){
                return resolve(JSON.parse(this.responseText));
            }
            if(this.status == 404){
                return reject(JSON.parse(this.responseText));
            }
        }
    });
}

function updateTable() {
    var namesAsString = $($("tbody>tr[align='left']")
        .map((i,obj)=>obj.children[0].innerText))
        .toArray().join(",")
    var f = createCopy(form);
    var sm = 0;
    f.children[0].children[0].value = namesAsString;
    makePostRequest(f,"/quote").then(data=>{
        console.log("table Update with",data);
        $("tbody>tr[align='left']").each((i,row)=>{
            row.children[3].innerText = `$${data[i].price}`;
            var val = (row.children[2].innerHTML * data[i].price).toFixed(2);
            row.children[4].innerText = `$${val}`;
            sm += val;
        });
    });
    $("tbody>tr:last").children()[1].innerText=`$${sm}`;
}

$('document').ready(()=>{
    var form1 = $("<form><div class='form-group'><input class='form-control' name='symbol' type='text' placeholder='symbol' autofocus></div></form>");
    var table1 = $("main>table");
    var btn1 = $("main>button");
    $('#quote').click(()=>{
        if($('main>form').length != 0)return;
        table1.attr("hidden","true");
        var f = createCopy(form1);
        btn1.text("Quote");
        btn1.removeAttr("hidden");
        $("main").prepend(f);
    });

    $("#buy").click(()=>{
        if($("main").find("form"))return;
        var f = createCopy(form1);
        var ip = createCopy(form1.find("input"));
        setAttribute(ip,["placeholder","type"],["No. of Shares","number"]);
        btn1.removeAttr("hidden");
        $("main").prepend(f);
    });

    $("main>button").click(()=> {
        var str = $("form>div>input");
        if(str.val() == "")return;
        makePostRequest($("form"),"/quote").then(data => {
            var p = $("main>p");
            if(p.length == 0){
                p=$("<p>");
                $("main").append(p);
            }
            p.text(`A share of ${data.name}(${data.symbol}) costs $${data.price}`);
        })
        .catch(response=>{
            console.warn(response);
        });
    });

    $("#home").click(()=>{
        var ff = $("main>form");
        if(ff.length != 0){
            ff.remove();
        }
        var p = $("main>p");
        if(p.length != 0){
            p.remove();
        }
        table1.removeAttr("hidden");
        btn1.attr("hidden","true");
    });
    // Updating table after 1min
    // setInterval(updateTable,300000);
});
