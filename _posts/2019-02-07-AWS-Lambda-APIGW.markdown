---
title: "AWS Lambda and API gateway: Integration struggles"
layout: "post"
date: 2019-02-07
---
The people at AWS made a great job with their [serverless tutorial](https://github.com/aws-samples/aws-serverless-workshops/tree/master/WebApplication).
The lambda code is using Node but I'd rather use Python instead. At first,
it looks like converting the code would be trivial but we hit one of the small
problems that makes serverless complex.

# Lambda proxy integration with API Gateway

In the API gateway integration, there is an option to forward all input context
(HTTP message but also some AWS specific data) to the Lambda function. In this particular
example, the information of the user that made the HTTP request is forwarded. All this
data should be available in the `event` parameter of the Lambda handler.

![Enabling Lambda proxy integration by ticking a box]({{ site.url}}/assets/serverless_lambda_proxy.PNG)

```js

exports.handler = (event, context, callback) => {
    if (!event.requestContext.authorizer) {
      errorResponse('Authorization not configured', context.awsRequestId, callback);
      return;
    }

    const rideId = toUrlString(randomBytes(16));
    console.log('Received event (', rideId, '): ', event);

    // Because we're using a Cognito User Pools authorizer, all of the claims
    // included in the authentication token are provided in the request context.
    // This includes the username as well as other attributes.
    const username = event.requestContext.authorizer.claims['cognito:username'];
    
    // ...
```

The `event.requestContext.authorizer` will contain all the authentication information.
That can be useful for example to insert data in a user-specific table in DynamoDB.

# Difference of implementation between languages

If using Python, the logical thing to do would be to use `event['requestContext']['authorizer']`.
Unfortunately, you will be rewarded with a KeyError if you use that code (as of Feb 2019).
The Python API does not expose the authorizer yet.

One solution to this problem is to throw away the Lambda proxy integration and use
mapping templates instead. Mapping templates will map the API Gateway request to the
Lambda request.

To configure this, you need to change the integration request of your API Gateway method.
First, untick the `Use Lambda proxy integration` box, then, in `Mapping Templates`, add 
a new mapping template for `application/json` (or whatever data format you receive).

I took the default templates (passthrough) and added some extra fields.

```json
##  See http://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-mapping-template-reference.html
##  This template will pass through all parameters including path, querystring, header, stage variables, and context through to the integration endpoint via the body/payload
#set($allParams = $input.params())

{
"body-json" : $input.json('$'),

"params" : {
#foreach($type in $allParams.keySet())
    #set($params = $allParams.get($type))
"$type" : {
    #foreach($paramName in $params.keySet())
    "$paramName" : "$util.escapeJavaScript($params.get($paramName))"
        #if($foreach.hasNext),#end
    #end
}
    #if($foreach.hasNext),#end
#end
},

"stage-variables" : {
#foreach($key in $stageVariables.keySet())
"$key" : "$util.escapeJavaScript($stageVariables.get($key))"
    #if($foreach.hasNext),#end
#end
},

"context" : {
    "identity" : {
        "sub" : "$context.authorizer.claims.sub",
        "email" : "$context.authorizer.claims.email"
    },
    "account-id" : "$context.identity.accountId",
    "api-id" : "$context.apiId",
    "api-key" : "$context.identity.apiKey",
    "authorizer-principal-id" : "$context.authorizer.principalId",
    "caller" : "$context.identity.caller",
    "cognito-authentication-provider" : "$context.identity.cognitoAuthenticationProvider",
    "cognito-authentication-type" : "$context.identity.cognitoAuthenticationType",
    "cognito-identity-id" : "$context.identity.cognitoIdentityId",
    "cognito-identity-pool-id" : "$context.identity.cognitoIdentityPoolId",
    "http-method" : "$context.httpMethod",
    "stage" : "$context.stage",
    "source-ip" : "$context.identity.sourceIp",
    "user" : "$context.identity.user",
    "user-agent" : "$context.identity.userAgent",
    "user-arn" : "$context.identity.userArn",
    "request-id" : "$context.requestId",
    "resource-id" : "$context.resourceId",
    "resource-path" : "$context.resourcePath"
    }
}

```

The authorizer data is mapped to the `context.identity`. In the Lambda, I can now access my user
info with `event['context']['identity']['email']` for example.

Anyway, I am considering whether using Lambda Proxy integration is a good idea. I'd rather know exactly
what is in my `event` object, and mapping templates give me that control.

`serverless` is a relatively new buzzword but it actually looks like I can deploy applications for almost
no cost as long as I don't have any users :D. Stay tuned for maybe other AWS adventures!
