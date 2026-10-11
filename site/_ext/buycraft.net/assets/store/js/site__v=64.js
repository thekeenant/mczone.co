$(document).ready(function() 
{
	$(".mc-skin").minecraftSkin({ scale: 2 });
	$(".mc-head").minecraftSkin({ draw: 'head', scale: 2 });

	$('.gateway-submit').click(function() {
	     $('#checkout-gateway').val(this.name)
	});
});

function submitCheckoutForm(form)
{
	$.ajax({
		type: 'POST',
	  	url: form.attr("action"),
	  	data: form.serialize(),
	  	dataType: "json",
	  	success: function(json)
	  	{
  			if(json.type == "error")
  			{
  				showNotification("error", json.message);
  			}
  			else if(json.type == "success")
  			{
  				if(json.gateway == "googlewallet")
  				{
  					google.payments.inapp.buy({
						jwt: json.data,
					    success: function() 
					    { 
					        window.top.location.replace("/checkout/complete");
					    }, 
					    failure: function(result) 
					    {
					    	error = result.response.errorType;
					    	
					    	if(error != 'PURCHASE_CANCELED' && error != 'PURCHASE_CANCELLED')
					    	{
					    		showNotification("error", "Your transaction could not be completed. (Error: " + error + ")");
					    	}
					    }
					});
  				}
  				else if(json.gateway == "stripe")
  				{
  					stripeData = json.data;

  					stripeData.token = function(stripeResponse)
			        {
			        	$.ajax({
							type: 'POST',
						  	url: "/checkout/stripe",
						  	data: { token: stripeResponse.id },
						  	dataType: "json",
						  	success: function(response)
						  	{
						  		if(response.complete)
						  		{
						  			window.top.location.replace("/checkout/complete");
						  		}
						  		else
						  		{
						  			showNotification("error", response.reason);
						  		}
						  	}
						 });
			        };

  					StripeCheckout.open(stripeData);
  				}
  				else
  				{
  					window.top.location.replace(json.data);
  				}
  			}
	  	},
	  	error: function(data)
	  	{
	  		showNotification("error", "We could not send you to the payment gateway - please refresh the page and try again.");
	  	}
	});	

	return false;
}