$(document).ready(function() {
    options = {
      search_contains: true,
    }
    $('#id_threats').chosen(options);
    $('#id_habitats').chosen(options);
    $('#id_references').chosen(options);
});