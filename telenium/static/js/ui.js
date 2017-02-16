var url = "ws://" + document.location.hostname + ":" + document.location.port + "/ws";
var socket = null;
var current_el = null;
var app_status = "stopped";
var test = null;
var current_test_id = null;
var latest_export = null;

function telenium_execute() {
    console.log("app_status", app_status)
    $("#btn-execute")
        .prop("disabled", true)
        .addClass("loading");
    if (app_status == "stopped")
        telenium_send("execute", {});
    else if (app_status == "running")
        telenium_send("stop", {});
}

function telenium_save_local() {
    telenium_send("save_local", {});
}

function telenium_add_env() {
    var template = $("#tpl-env-new").html();
    var rendered = Mustache.render(template, {});
    $("#tl-env").append(rendered);
}

function telenium_add_step() {
    var template = $("#tpl-step-new").html();
    var rendered = Mustache.render(template, {});
    $("#tl-steps").append(rendered);
    telenium_sync_test();
}

function telenium_remove_env(ev) {
    $($(ev).parents()[1]).detach();
    telenium_sync_env();
}

function _telenium_ev_step_to_row(ev) {
    var parents = $(ev).parentsUntil("tbody");
    return parents[parents.length - 1];
}

function telenium_remove_step(ev) {
    $(_telenium_ev_step_to_row(ev)).detach();
    telenium_sync_test();
}

function telenium_duplicate_step(ev) {
    var parent = _telenium_ev_step_to_row(ev);
    $(parent).clone().insertAfter(parent);
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
    $(current_el).parent().find("input.selector").val(selector);
    telenium_sync_test();
}

function telenium_play_step(el) {
    var index = $(el).parents("tr")[0].rowIndex - 1;
    telenium_send("run_step", {
        "id": current_test_id,
        "index": index
    });
}

function telenium_run_steps() {
    $(".test-status").hide();
    telenium_send("run_steps", {
        "id": current_test_id
    });
}

function telenium_run_tests() {
    $(".test-status").hide();
    telenium_send("run_tests", {});
}

function telenium_add_test() {
    current_test_id = null;
    telenium_send("add_test", {});
}

function telenium_clone_test() {
    telenium_send("clone_test", {"test_id": current_test_id});
    current_test_id = null;
}

function telenium_process(msg) {
    cmd = msg[0];
    console.log(msg)
    if (cmd == "settings") {
        $.each(msg[1], function(key, value) {
            $("input[data-settings-key='" + key + "']").val(value);
        })

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
        if (current_test_id === null)
            current_test_id = msg[1][msg[1].length - 1]["id"];
        app_sync_tests_choice(msg[1]);
        telenium_select_test(current_test_id);

    } else if (cmd == "test") {
        test = msg[1];
        current_test_id = test["id"];
        app_sync_test();

    } else if (cmd == "status") {
        app_status = msg[1];
        if (msg[1] == "running") {
            $("#btn-execute")
                .prop("disabled", false)
                .removeClass("loading")
                .find("span")
                .removeClass("glyphicon-play")
                .addClass("glyphicon-stop");
        } else if (msg[1] == "stopped") {
            $("#btn-execute")
                .prop("disabled", false)
                .removeClass("loading")
                .find("span")
                .removeClass("glyphicon-stop")
                .addClass("glyphicon-play");
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
                tpl = Mustache.render(template, {
                    "selectors": selectors
                });
                $("#modal-pick .modal-body").html(tpl);
                $("#modal-pick").modal("show");
            }
        }

    } else if (cmd == "run_test") {

    } else if (cmd == "run_step") {
        var test_id = msg[1];
        var rowindex = msg[2];
        var status = msg[3];
        if (test_id != current_test_id)
            return;
        var tr = $("#tl-steps tr").eq(rowindex);
        tr.find(".test-status").hide();
        tr.find(".test-status-" + status).show();

    } else if (cmd == "export") {
        latest_export = {
            "data": msg[1],
            "mimetype": msg[2],
            "filename": msg[3],
            "type": msg[4]
        }
        $("#modal-export").modal("show");
        $("#modal-export .modal-body pre").html(latest_export["data"]);

    } else if (cmd == "progress") {
        if (msg[1] == "started") {
            $(".progress-box").removeClass("hidden");
            app_set_progress("0");
        } else if (msg[1] == "update") {
            var count = msg[2];
            var total = msg[3]
            if (total > 0)
                app_set_progress("" + Math.round(count * 100 / total));
        } else {
            $(".progress-box").addClass("hidden");
        }
    } else if (cmd == "changed") {
        $("#btn-save").prop("disabled", !msg[1]);
    } else if (cmd == "is_local") {
        $("#btn-save").show();
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


function telenium_sync_settings() {
    var settings = {};
    $("input[data-settings-key]").each(function(index, item) {
        settings[$(this).data("settings-key")] = $(this).val();
    })
    telenium_send("sync_settings", {
        "settings": settings
    });
}


function telenium_sync_test() {
    var t_types = $.map($("#tl-steps select"), function(item) {
        return $(item).val();
    })
    var t_selectors = $.map($("#tl-steps input.step-selector"), function(item) {
        return $(item).val();
    })
    var t_args1 = $.map($("#tl-steps input.step-arg1"), function(item) {
        return $(item).val();
    })
    var t_args2 = $.map($("#tl-steps input.step-arg2"), function(item) {
        return $(item).val();
    })
    var steps = [];
    for (var i = 0; i < t_types.length; i++) {
        steps.push([t_types[i], t_selectors[i], t_args1[i], t_args2[i]]);
    }
    telenium_send("sync_test", {
        "id": current_test_id,
        "name": $("input[data-test-key='name']").val(),
        "steps": steps
    });
}

function telenium_delete_test() {
    if (current_test_id === null)
        return;
    telenium_send("delete_test", {
        "id": current_test_id
    });
    current_test_id = null;
}

function telenium_select(selector) {
    telenium_send("select", {
        "selector": selector
    });
}

function telenium_select_test(test_id) {
    current_test_id = test_id;
    telenium_send("select_test", {
        "id": test_id
    });
}

function telenium_export_python() {
    telenium_send("export", {
        "type": "python"
    });
}

function telenium_export_json() {
    telenium_send("export", {
        "type": "json"
    });
}

function app_show_page(page) {
    $(".navpage").removeClass("active");
    $(".navpage[data-page=" + page + "]").addClass("active");
    $(".page").addClass("hidden");
    $("#page-" + page).removeClass("hidden");
}

function app_sync_test() {
    if (current_test_id === null) {
        current_test_id = test["id"];
    }
    $("#tl-steps").empty();
    $("input[data-test-key='name']").val(test["name"]);

    var steps = test["steps"];
    template = $("#tpl-step-new").html();
    for (var i = 0; i < steps.length; i++) {
        var entry = steps[i];
        var tpl = $(Mustache.render(template, {
            "key": entry[0],
            "selector": entry[1],
            "arg1": entry[2],
            "arg2": entry[3]
        }));
        tpl.find("option[value=" + entry[0] + "]")
            .attr("selected", true);
        $("#tl-steps").append(tpl);
        $("#tl-steps select").change();
    }
}

function app_sync_tests_choice(tests) {
    $("#tl-tests").empty();
    for (var i = 0; i < tests.length; i++) {
        var option = $("<option></option>")
            .val(tests[i]["id"])
            .html(tests[i]["name"]);
        if (tests[i]["id"] == current_test_id) {
            option.prop("selected", true);
        }
        option.appendTo($("#tl-tests"));
    }
}

function app_set_progress(value) {
    $(".progress-box .progress-bar").css("width", "" + value + "%");
}

var textFile = null;

function makeTextFile(text, mimetype) {
    var data = new Blob([text], {
        type: mimetype
    });
    if (textFile !== null) {
        window.URL.revokeObjectURL(textFile);
    }
    textFile = window.URL.createObjectURL(data);
    return textFile;
}

function app_export_save() {
    var link = document.createElement("a");
    link.setAttribute("download", latest_export["filename"]);
    link.href = makeTextFile(latest_export["data"], latest_export["mimetype"]);
    window.requestAnimationFrame(function() {
        var event = new MouseEvent("click");
        link.dispatchEvent(event);
        document.body.removeChild(link);
    });
}

$(document).ready(function() {
    $(".navpage").click(function(ev, el) {
        app_show_page($(this).data("page"));
    })
    $("#btn-execute").click(telenium_execute);
    $("#btn-add-test").click(telenium_add_test);
    $("#btn-clone-test").click(telenium_clone_test);
    $("#btn-add-step").click(telenium_add_step);
    $("#btn-add-env").click(telenium_add_env);
    $("#btn-save").click(telenium_save_local);
    $("#btn-run-steps").click(telenium_run_steps);
    $("#btn-run-tests").click(telenium_run_tests);
    $("#btn-delete-test").click(telenium_delete_test);
    $("#btn-export-python").click(telenium_export_python);
    $("#btn-export-json").click(telenium_export_json);
    $("#btn-export-save").click(app_export_save);
    $("#tl-env").on("blur", "input", function() {
        telenium_sync_env();
    });
    $("#tl-tests").on("change", function() {
        telenium_select_test($(this).val());
    });
    $("input[data-settings-key]").on("blur", function() {
        telenium_sync_settings();
    });
    $("input[data-test-key]").on("change", function() {
        $("option[value='" + current_test_id + "']").html($(this).val());
        telenium_sync_test();
    });
    $("#tl-steps").on("blur", "select,input", function() {
        telenium_sync_test();
    });
    $("#tl-steps").on("change", "select", function() {
        var parent = $($(this).parents()[1]);
        var container = parent.find(".step-arg-container");
        var selected = $(this).find(":selected");
        if (typeof selected.data("arg0") === "undefined") {
            parent.find(".step-selector")
                .prop("placeholder", 'XPATH selector like //Button[@text~="Hello"]');
        } else {
            parent.find(".step-selector")
                .prop("placeholder", selected.data("arg0"));
        }

        if (typeof selected.data("arg1") === "undefined") {
            container.hide();
            return;
        }
        container.find(".step-arg1").prop("placeholder", selected.data("arg1"));
        if (typeof selected.data("arg2") === "undefined") {
            container.find(".step-arg2").hide();
        } else {
            container.find(".step-arg2")
                .prop("placeholder", selected.data("arg2"))
                .show();
        }

        container.show();

    }).on("input", "input.step-selector", function(ev) {
        current_el = ev.target;
        telenium_select($(current_el).val());
    }).on("focus", "input.step-selector", function(ev) {
        current_el = ev.target;
        telenium_select($(current_el).val());
    }).on("blur", "input.step-selector", function(ev) {
        current_el = ev.target;
        telenium_select("");
    });

    $("#tl-steps-container").sortable({
        containerSelector: "table",
        itemPath: "> tbody",
        itemSelector: "tr",
        placeholder: "<tr class='placeholder'/>",
        onDrop: function($item, container, _super) {
            _super($item, container);
            telenium_sync_test()
        }
    });

    telenium_connect();
});
