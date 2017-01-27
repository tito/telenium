function telenium_execute() {
};

function telenium_add_command() {
    console.log("hello")
    var template = $("#tpl-command-new").html();
    Mustache.parse(template);
    var rendered = Mustache.render(template, {name: "Luke"});
    $("#tl-cmd").append(rendered);
};

function telenium_remove_command(ev) {
    $($(ev).parents()[1]).detach();
}

$(document).ready(function() {
    $("#btn-execute").click(telenium_execute);
    $("#btn-add-command").click(telenium_add_command);
});
