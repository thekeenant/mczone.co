var notificationBar;

$(function() 
{
    $(".datepicker").datepicker({ dateFormat: "dd-mm-yy" });

    $(".popover-help").live("click", function()
    {
    	$(this).popover('show');

    	return false;
    });

    $('.popover-help').live("hover", function(){}, function()
    {
    	$(this).popover('destroy');
    });

    $('.tooltip-help').hover(function()
    {
    	$(this).tooltip('show');
    }, 
    function()
    {
    	$(this).tooltip('destroy');
    });

    $("img[data-src]").jail();
});

// Fix for Jquery UI sortable
function sortableTableWidthFix(e, ui) 
{
	ui.children().each(function() 
	{
		$(this).width($(this).width());
	});
	
	return ui;
}

function submitForm(form, clearOnSuccess)
{
	if(clearOnSuccess == undefined) clearOnSuccess = false;

	var submit = form.find("input[type='submit']");
	var oldButtonValue = submit.val();

	submit.attr("disabled", "true");
    submit.attr("value", "Loading...");

	$.ajax({
		type: 'POST',
	  	url: form.attr("action"),
	  	data: form.serialize(),
	  	dataType: "json",
	  	success: function(data)
	  	{
	  		if(data.type == 'success' && data.success_url != data.error_url)
	  		{
	  			window.location.replace(data.success_url);	  			
	  		}
	  		else
	  		{
	  			if(data.type == "success" && clearOnSuccess)
	  			{
	  				form.each(function()
	  				{
					    this.reset();
					});
	  			}
	  				
	  			if(typeof Recaptcha !== 'undefined')
	  			{
	  				Recaptcha.reload();
	  			}

	  			if(data.type == "error")
	  			{
	  				submit.attr("value", oldButtonValue);
	  				submit.removeAttr("disabled");

	  				showNotification("error", data.message);
	  			}
	  			else
	  			{
	  				submit.removeClass("btn-primary");
	  				submit.addClass("btn-success");
					submit.attr("value", "Saved");

					setTimeout(function() {
						submit.removeClass("btn-success");
	  					submit.addClass("btn-primary");
						submit.removeAttr("disabled");
						submit.attr("value", oldButtonValue);
					}, 2000);

					hideNotificationBar();
	  			}
	  		}
	  	},
	  	error: function(data)
	  	{
	  		submit.attr("value", oldButtonValue);
	  		submit.removeAttr("disabled");

	  		showNotification("error", "Internal error - please reload the page and try submitting the form again.");
	  	}
	});	

	return false;
}

function showModal(url)
{
	$.ajax({
         url: url,
         success: function(data) 
         {
         	$('#popupModal').html(data);
			$('#popupModal').modal("show");

			$(".datepicker").datepicker({ dateFormat: "dd-mm-yy" });
         },
         async: true
    });          

	return false;
}

function showNotification(type, message)
{
	clearTimeout(notificationBar);

	$("html, body").animate({ scrollTop: $("body").offset().top - 100 }, "fast");

	$('#popupModal').modal('hide');

	$("#notification-bar").removeClass();
	$("#notification-bar").addClass(type);
	$('#notification-bar').slideDown(200);
	$('#notification-bar').html(message);

	notificationBar = setTimeout(function() { 
		$('#notification-bar').slideUp(); 
	}, 5000);
}

function hideNotificationBar()
{
	clearTimeout(notificationBar);

	$('#notification-bar').slideUp();
}