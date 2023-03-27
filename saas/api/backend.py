# Copyright (c) 2022, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#pylint:disable=useless-super-delegation

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (RetrieveAPIView,
    RetrieveUpdateDestroyAPIView)
from rest_framework.response import Response

from ..backends import ProcessorError
from ..compat import gettext_lazy as _
from ..docs import OpenAPIResponse, swagger_auto_schema, Parameter, IN_PATH
from ..mixins import OrganizationMixin
from ..models import get_broker
from .serializers import (BankSerializer, CardSerializer,
    CardTokenSerializer)


class RetrieveBankAPIView(OrganizationMixin, RetrieveAPIView):
    """
    Retrieves a payout account

    Pass through that calls the payment processor API to retrieve some details
    about the deposit account associated to a provider (if that information is
    available through the :doc:`payment processor backend<backends>` API).

    This API does not trigger payment of a subscriber to a provider. Checkout
    of a subscription cart is done either through the
    :ref:`HTML page <pages_cart>` or
    :ref:`API end point <api_checkout>`.

    **Tags**: billing, provider, profilemodel

    **Examples**

    .. code-block:: http

        GET /api/billing/cowork/bank HTTP/1.1

    responds

    .. code-block:: json

        {
          "bank_name": "Stripe Test Bank",
          "last4": "***-htrTZ",
          "balance_amount": 0,
          "balance_unit": "usd"
        }
    """
    serializer_class = BankSerializer

    def retrieve(self, request, *args, **kwargs):
        #pylint: disable=unused-argument
        return Response(
            self.organization.retrieve_bank())


class PaymentMethodDetailAPIView(OrganizationMixin,
                                 RetrieveUpdateDestroyAPIView):
    """
    Retrieves a payment method

    Pass through to the payment processor to retrieve some details about
    the payment method (ex: credit card) associated to a subscriber.

    When you wish to update the payment method on file through
    a Strong Customer Authentication (SCA) workflow, the payment processor
    will require a token generated by the server. That token can be retrieved
    in the processor.STRIPE_INTENT_SECRET field when the API is called
    with `?update=1` query parameters.

    The API is typically used within an HTML
    `update payment method page </docs/guides/themes/#dashboard_billing_card>`_
    as present in the default theme.

    **Tags**: billing, subscriber, profilemodel

    **Examples**

    .. code-block:: http

        GET /api/billing/xia/card HTTP/1.1

    responds

    .. code-block:: json

        {
          "last4": "1234",
          "exp_date": "12/2019"
        }
    """
    serializer_class = CardSerializer

    def get_serializer_class(self):
        if self.request.method.lower() in ('put',):
            return CardTokenSerializer
        return super(PaymentMethodDetailAPIView, self).get_serializer_class()

    def delete(self, request, *args, **kwargs):
        """
        Deletes a payment method

        Pass through to the payment processor to remove the payment method
        (ex: credit card) associated to a subscriber.

        The API is typically used within an HTML
        `update payment method page </docs/guides/themes/#dashboard_billing_card>`_
        as present in the default theme.

        **Tags**: billing, subscriber, profilemodel

        **Examples**

        .. code-block:: http

            DELETE /api/billing/xia/card HTTP/1.1
        """
        return super(PaymentMethodDetailAPIView, self).delete(
            request, *args, **kwargs)

    @swagger_auto_schema(
        manual_parameters=[
            Parameter('update', IN_PATH, type='bool')
        ])
    def get(self, request, *args, **kwargs):
        return super(PaymentMethodDetailAPIView, self).get(
            request, *args, **kwargs)

    @swagger_auto_schema(responses={
        200: OpenAPIResponse("Update successful", CardSerializer),
    })
    def put(self, request, *args, **kwargs):
        """
        Updates a payment method

        Pass through to the payment processor to update some details about
        the payment method (ex: credit card) associated to a subscriber.

        The API is typically used within an HTML
     `update payment method page </docs/guides/themes/#dashboard_billing_card>`_
        as present in the default theme.

        **Tags**: billing, subscriber, profilemodel

        **Examples**

        .. code-block:: http

            PUT /api/billing/xia/card HTTP/1.1

        .. code-block:: json

            {
              "token": "xyz"
            }

        responds

        .. code-block:: json

            {
              "last4": "1234",
              "exp_date": "12/2019"
            }
        """
        return super(PaymentMethodDetailAPIView, self).put(
            request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        #pylint:disable=unused-argument
        self.organization.delete_card()
        return Response({
            'detail': _("Your credit card is no longer on file with us.")},
            status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        #pylint:disable=unused-argument
        resp_data = self.organization.retrieve_card()
        if request.query_params.get('update', False):
            broker = get_broker()
            resp_data.update({
                'processor':
                broker.processor_backend.get_payment_context(# card update
                    self.organization,
                    provider=broker, broker=broker)
            })
        return Response(resp_data)

    def update(self, request, *args, **kwargs):
        #pylint:disable=unused-argument
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer_class()(
            data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data.get('token')
        try:
            new_card = self.organization.update_card(token, self.request.user)
        except ProcessorError as err:
            raise ValidationError(err)
        new_card.update({
            'detail': _("Your credit card on file was sucessfully updated.")})
        return Response(new_card)