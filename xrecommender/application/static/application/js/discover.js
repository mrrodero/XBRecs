$(document).ready(function() {
    $('#search-form').on('submit', function(event) {
        event.preventDefault();
        var query = $('#search-input').val();
        $.ajax({
            url: searchUrl,
            data: {
                'q': query
            },
            success: function(data) {
                $('#search-results').html(data);
            },
            error: function(error) {
                console.error('Error:', error);
            }
        });
    });
});