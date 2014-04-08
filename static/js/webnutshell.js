$(document).ready(function() {

    /**
     * AJAX Node_Snapshot Search Filter
     */
    $("#log-search").keyup(function() {
       var content = $("#log-search").val();
       if(content.length >= 0) {
           $.getJSON("/logs/search", {"value": content}, function(data) {
               $("#log-table tbody tr").remove();
               for(var i=0;i<data.length;i++) {
                   var html = "<tr>";
                   html += "<td><a href=\"/logs/show/"+data[i].id+"\">"+data[i].name+"</a></td>";
                   html += "<td><a href=\"/customers/show/"+data[i].customer+"\">To Customer</a></td>";
                   html += "<td>";
                   html += "<a class=\"btn btn-small btn-warning\" href=\"/logs/edit/"+data[i].id+"\">Edit</a>\n";
                   html += "<a class=\"btn btn-small btn-danger\" href=\"/logs/delete/"+data[i].id+"\">Delete</a>";
                   html += "</td>";
                   html += "</tr>";
                   $("#log-table tbody").append(html);
               }
           });
       }
    });

    /**
     * AJAX Customer Search Filter
     */
    $("#customer-search").keyup(function() {
       var content = $("#customer-search").val();
       if(content.length >= 0) {
           $.getJSON("/customers/search", {"value": content}, function(data) {
               $("#customer-table tbody tr").remove();
               for(var i=0;i<data.length;i++) {
                   var html = "<tr>";
                   html += "<td><a href=\"/customers/show/"+data[i].id+"\">"+data[i].name+"</a></td>";
                   html += "<td>";
                   html += "<a class=\"btn btn-small btn-danger\" href=\"/logs/delete/"+data[i].id+"\">Delete</a>";
                   html += "</td>";
                   html += "</tr>";
                   $("#customer-table tbody").append(html);
               }
           });
       }
    });

});
