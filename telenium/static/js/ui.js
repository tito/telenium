var editor = {
    commands: [
        {id: 0, name: "waitForElement", selector: "//TextInput", value:""}
    ],
    selectedId: null
};

var CommandView = React.createClass({
    onDelete: function(e) {
        this.props.onDeleteCommand(this.props.command.id);
    },

    render: function() {
        var command = this.props.command;
        var editor = this.props.editor;
        var cx = React.addons.classSet;
        var classes = cx({
            "bg-success": editor.selectedId === command.id
        });
        return (
            <tr key={command.id}
                 className={classes}
                 onClick={this.props.onSelectCommand.bind(null, command.id)}>
                <td className="col-md-4">{command.name}</td>
                <td className="col-md-3">{command.selector}</td>
                <td className="col-md-3">{command.value}</td>
                <td className="col-md-3">
                    <button className="btn btn-danger" onClick={this.onDelete}>Delete</button>
                </td>
            </tr>
        );
    }
});

var CommandEditor = React.createClass({
    getInitialState: function() {
        return {
            name: "",
            selector: "",
            value: ""
        }
    },

    onChange: function(e) {
        this.props.onChangeCommand(
            this.props.command.id, e.target.name, e.target.value);
    },

    onDelete: function(e) {
        this.props.onDeleteCommand(this.props.command.id);
    },

    render: function() {
        return (
            <tr>
            <td className="col-md-4">
                <input type="text" name="name" className="form-control" value={this.props.command.name} onChange={this.onChange}/>
            </td><td className="col-md-3">
                <input type="text" name="selector" className="form-control" value={this.props.command.selector} onChange={this.onChange}/>
            </td><td className="col-md-3">
                <input type="text" name="value" className="form-control" value={this.props.command.value} onChange={this.onChange}/>
            </td>
            <td className="col-md-3">
                <button className="btn btn-danger" onClick={this.onDelete}>Delete</button>
            </td>
            </tr>
        );
    }
});

var CommandEditable = React.createClass({
    render: function() {
        var ui = null;
        var command = this.props.command;
        var editor = this.props.editor;

        if (this.props.editor.selectedId === command.id) {
            ui = <CommandEditor command={command}
              onChangeCommand={this.props.onChangeCommand}
              onDeleteCommand={this.props.onDeleteCommand}/>
        } else {
            ui = <CommandView key={command.id} command={command} editor={editor}
                onSelectCommand={this.props.onSelectCommand}
                onDeleteCommand={this.props.onDeleteCommand}/>
        }

        return ui;
    }
});

var CommandsList = React.createClass({
    render: function() {
        var editor = this.props.editor;
        var onSelectCommand = this.props.onSelectCommand;
        var onChangeCommand = this.props.onChangeCommand;

        return (
            <table className="table">
            <thead>
                <tr>
                    <th>Command</th>
                    <th>Selector</th>
                    <th>Value</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
            {
                this.props.commands.map(function(command) {
                    return <CommandEditable editor={editor} command={command}
                        onSelectCommand={onSelectCommand}
                        onDeleteCommand={onDeleteCommand}
                        onChangeCommand={onChangeCommand}
                    />;
                })
            }
            </tbody>
            </table>
        );
    }
});

var Editor = React.createClass({
    render: function() {
        var editor = this.props.editor;
        return (
            <div id="editor">
                <h2>Tests</h2>
                <CommandsList editor={editor} commands={editor.commands}
                    onChangeCommand={this.props.onChangeCommand}
                    onSelectCommand={this.props.onSelectCommand}
                    onDeleteCommand={this.props.onDeleteCommand}/>
                <div>
                    <button onClick={this.props.onAddCommand}>Add command</button>
                </div>
            </div>
        );
    }
});

var nextCommandId = 1;
var onAddCommand = function() {
    var command = {id: nextCommandId, name: "", selector: "", value: ""};
    nextCommandId++;
    editor.commands.push(command);
    editor.selectedId = command.id;
    onChange();
};

var onChangeCommand = function(id, key, value) {
    var command = _.find(editor.commands, function(command) {
        return command.id === id;
    })
    if (command) {
        command[key] = value;
    };
    onChange();
};

var onDeleteCommand = function(id) {
    var command = _.find(editor.commands, function(command) {
        return command.id === id;
    })
    editor.commands.pop(command);
    onChange();
}

var onSelectCommand = function(id) {
    editor.selectedId = id;
    onChange();
};


var Launcher = React.createClass({
    getInitialState: function() {
        return {
            command: "python /home/tito/code/kivy/examples/showcase/main.py",
            args: ""
        }
    },

    execute: function() {

    },

    render: function() {
        return (
            <div>
                <h2>Execute</h2>
                <div className="form-group">
                    <label for="command">Command</label>
                    <input className="form-control" value={this.state.command}/>
                </div>
                <div className="form-group">
                    <label for="args">Arguments</label>
                    <input className="form-control" value={this.state.args}/>
                </div>
                <button onClick={this.execute} class="btn btn-default">Execute</button>
            </div>
        )
    }
});

var onChange = function() {
    React.render(
        <div>
            <Launcher/>
            <Editor editor={editor}
                onAddCommand={onAddCommand}
                onChangeCommand={onChangeCommand}
                onSelectCommand={onSelectCommand}
                onDeleteCommand={onDeleteCommand}/>
        </div>,
        document.getElementById("editor")
    );
};

onChange();
