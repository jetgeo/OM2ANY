function readJson() {
    fetch("C:\\Users\\JETKNU\\OneDrive - Statens Kartverk\\Forskningsdata\\OvertureMaps\\schema\\defs.json")
        .then((res) => {
        return res.json();
    })
    .then((data) => console.log(data));
}

readJson();
