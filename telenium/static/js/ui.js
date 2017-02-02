var url = "ws://" + document.location.hostname + ":" + document.location.port + "/ws";
var socket = null;
var current_el = null;

function telenium_execute() {
    telenium_send("execute", {});
}

function telenium_add_env() {
    var template = $("#tpl-env-new").html();
    var rendered = Mustache.render(template, {});
    $("#tl-env").append(rendered);
}

function telenium_add_test() {
    var template = $("#tpl-test-new").html();
    var rendered = Mustache.render(template, {
        name: "Luke"
    });
    $("#tl-tests").append(rendered);
}

function telenium_remove_env(ev) {
    $($(ev).parents()[1]).detach();
    telenium_sync_env();
}

function telenium_remove_test(ev) {
    $($(ev).parents()[1]).detach();
    telenium_sync_tests();
}

function telenium_connect() {
    socket = new ReconnectingWebSocket(url, null, {
        automaticOpen: false
    })
    socket.onmessage = function(event) {
        var msg = JSON.parse(event.data);
        telenium_process(msg);
    };
    socket.onopen = function() {
        telenium_send("recover")
    }
    socket.open();
}

function telenium_send(command, options) {
    var data = {
        "cmd": command,
        "options": options || {}
    };
    socket.send(JSON.stringify(data));
}

function telenium_pick(el) {
    current_el = el;
    $("#modal-pick-wait").modal();
    telenium_send("pick", {});
}

function telenium_pick_use(selector) {
    $("#modal-pick").modal("hide");
    $(current_el).parent().find("input.arg").val(selector);
    telenium_sync_tests();
}

function telenium_play_test(el) {
    var index = $(el).parents("tr")[0].rowIndex - 1;
    telenium_send("run_test", {"index": index});
}

function telenium_play_all() {
    $(".test-status").hide();
    telenium_send("run_tests", {});
}

function telenium_process(msg) {
    cmd = msg[0];
    console.log(msg)
    if (cmd == "entrypoint") {
        $("#tl-entrypoint").val(msg[1]);
    } else if (cmd == "env") {
        $("#tl-env").empty();
        template = $("#tpl-env-new").html();
        for (var i = 0; i < msg[1].length; i++) {
            var entry = msg[1][i];
            tpl = Mustache.render(template, {
                "key": entry[0],
                "value": entry[1]
            });
            $("#tl-env").append(tpl);
        }
    } else if (cmd == "tests") {
        $("#tl-tests").empty();
        template = $("#tpl-test-new").html();
        for (var i = 0; i < msg[1].length; i++) {
            var entry = msg[1][i];
            var tpl = $(Mustache.render(template, {
                "key": entry[0],
                "value": entry[1]
            }));
            tpl.find("option[value=" + entry[0] + "]")
                .attr("selected", true);
            $("#tl-tests").append(tpl);
        }
    } else if (cmd == "status") {
        if (msg[1] == "running") {
            $("#btn-execute").prop("disabled", true).html("Running...");
        } else if (msg[1] == "stopped") {
            $("#btn-execute").prop("disabled", false).html("Start");
        }
    } else if (cmd == "pick") {
        $("#modal-pick-wait").modal("hide");
        if (msg[1] == "error") {
            alert("Application is not running");
        } else {
            var selectors = msg[2];
            if (selectors.length == 1) {
                telenium_pick_use(selectors[0]);
            } else if (selectors.length > 1) {
                template = $("#tpl-pick-list").html();
                tpl = Mustache.render(template, {"selectors": selectors});
                $("#modal-pick .modal-body").html(tpl);
                $("#modal-pick").modal("show");
            }
        }
    } else if (cmd == "run_test") {
        var rowindex = msg[1];
        var status = msg[2];
        var tr = $("#tl-tests tr").eq(rowindex);
        tr.find(".test-status").hide();
        tr.find(".test-status-" + status).show();
    } else if (cmd == "export") {
        $("#modal-export").modal("show");
        $("#modal-export .modal-body pre").html(msg[2]);
    }
}

function telenium_sync_env() {
    var keys = $.map($("#tl-env input[name='key[]']"), function(item) {
        return $(item).val();
    })
    var values = $.map($("#tl-env input[name='value[]']"), function(item) {
        return $(item).val();
    })
    var env = {};
    for (var i = 0; i < keys.length; i++) {
        if (keys[i] == "")
            continue;
        env[keys[i]] = values[i];
    }
    telenium_send("sync_env", {
        "env": env
    });
}


function telenium_sync_entrypoint() {
    telenium_send("sync_entrypoint", {
        "entrypoint": $("#tl-entrypoint").val()
    });
}


function telenium_sync_tests() {
    var t_types = $.map($("#tl-tests select"), function(item) {
        return $(item).val();
    })
    var t_args = $.map($("#tl-tests input.arg"), function(item) {
        return $(item).val();
    })
    var tests = [];
    for (var i = 0; i < t_types.length; i++) {
        tests.push([t_types[i], t_args[i]]);
    }
    telenium_send("sync_tests", {
        "tests": tests
    });
}

function telenium_select(selector) {
    telenium_send("select", {"selector": selector});
}

function telenium_export_python() {
    telenium_send("export", {"type": "python"});
}

function telenium_export_json() {
    telenium_send("export", {"type": "json"});
}


$(document).ready(function() {
    $("#btn-execute").click(telenium_execute);
    $("#btn-add-test").click(telenium_add_test);
    $("#btn-add-env").click(telenium_add_env);
    $("#btn-play-all").click(telenium_play_all);
    $("#btn-export-python").click(telenium_export_python);
    $("#btn-export-json").click(telenium_export_json);
    $("#tl-env").on("blur", "input", function() {
        telenium_sync_env();
    });
    $("#tl-entrypoint").on("blur", function() {
        telenium_sync_entrypoint();
    });
    $("#tl-tests").on("blur", "select,input", function() {
        telenium_sync_tests();
    });
    $("#tl-tests").on("input", "input.arg", function(ev) {
        current_el = ev.target;
        telenium_select($(current_el).val());
    }).on("focus", "input.arg", function(ev) {
        current_el = ev.target;
        telenium_select($(current_el).val());
    }).on("blur", "input.arg", function(ev) {
        current_el = ev.target;
        telenium_select("");
    });
    telenium_connect();
});
