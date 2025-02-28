# This file is part of the Trezor project.
#
# Copyright (C) 2020 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import pytest

from trezorlib import btc, device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...tx_cache import TxCache
from .payment_req import make_payment_request
from .signtx import request_finished, request_input, request_output, request_payment_req

B = messages.ButtonRequestType

TX_CACHE_TESTNET = TxCache("Testnet")
TX_CACHE_MAINNET = TxCache("Bitcoin")

FAKE_TXHASH_e5b7e2 = bytes.fromhex(
    "e5b7e21b5ba720e81efd6bfa9f854ababdcddc75a43bfa60bf0fe069cfd1bb8a"
)
FAKE_TXHASH_f982c0 = bytes.fromhex(
    "f982c0a283bd65a59aa89eded9e48f2a3319cb80361dfab4cf6192a03badb60a"
)

PIN = "1234"
ROUND_ID_LEN = 32
SLIP25_PATH = parse_path("m/10025h")

pytestmark = pytest.mark.skip_t1


@pytest.mark.setup_client(pin=PIN)
def test_sign_tx(client: Client):
    # NOTE: FAKE input tx

    commitment_data = b"\x0fwww.example.com" + (1).to_bytes(ROUND_ID_LEN, "big")

    with client:
        client.use_pin_sequence([PIN])
        btc.authorize_coinjoin(
            client,
            coordinator="www.example.com",
            max_rounds=2,
            max_coordinator_fee_rate=50_000_000,  # 0.5 %
            max_fee_per_kvbyte=3500,
            n=parse_path("m/10025h/1h/0h/1h"),
            coin_name="Testnet",
            script_type=messages.InputScriptType.SPENDTAPROOT,
        )

    client.call(messages.LockDevice())

    with client:
        client.set_expected_responses(
            [messages.PreauthorizedRequest, messages.OwnershipProof]
        )
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=commitment_data,
            preauthorized=True,
        )

    with client:
        client.set_expected_responses(
            [messages.PreauthorizedRequest, messages.OwnershipProof]
        )
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/5"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=commitment_data,
            preauthorized=True,
        )

    inputs = [
        messages.TxInputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # m/10025h/1h/0h/1h/0/0
            # tb1pkw382r3plt8vx6e22mtkejnqrxl4z7jugh3w4rjmfmgezzg0xqpsdaww8z
            amount=100_000,
            prev_hash=FAKE_TXHASH_e5b7e2,
            prev_index=0,
            script_type=messages.InputScriptType.EXTERNAL,
            script_pubkey=bytes.fromhex(
                "5120b3a2750e21facec36b2a56d76cca6019bf517a5c45e2ea8e5b4ed191090f3003"
            ),
            ownership_proof=bytearray.fromhex(
                "534c001901019cf1b0ad730100bd7a69e987d55348bb798e2b2096a6a5713e9517655bd2021300014052d479f48d34f1ca6872d4571413660040c3e98841ab23a2c5c1f37399b71bfa6f56364b79717ee90552076a872da68129694e1b4fb0e0651373dcf56db123c5"
            ),
            commitment_data=commitment_data,
        ),
        messages.TxInputType(
            address_n=parse_path("m/10025h/1h/0h/1h/1/0"),
            amount=7_289_000,
            prev_hash=FAKE_TXHASH_f982c0,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDTAPROOT,
        ),
    ]

    outputs = [
        # Other's coinjoined output.
        messages.TxOutputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # m/10025h/1h/0h/1h/1/0
            address="tb1pupzczx9cpgyqgtvycncr2mvxscl790luqd8g88qkdt2w3kn7ymhsrdueu2",
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
            payment_req_index=0,
        ),
        # Our coinjoined output.
        messages.TxOutputType(
            # tb1phkcspf88hge86djxgtwx2wu7ddghsw77d6sd7txtcxncu0xpx22shcydyf
            address_n=parse_path("m/10025h/1h/0h/1h/1/1"),
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOTAPROOT,
            payment_req_index=0,
        ),
        # Our change output.
        messages.TxOutputType(
            # tb1pchruvduckkwuzm5hmytqz85emften5dnmkqu9uhfxwfywaqhuu0qjggqyp
            address_n=parse_path("m/10025h/1h/0h/1h/1/2"),
            amount=7_289_000 - 50_000 - 36_445 - 490,
            script_type=messages.OutputScriptType.PAYTOTAPROOT,
            payment_req_index=0,
        ),
        # Other's change output.
        messages.TxOutputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # m/10025h/1h/0h/1h/1/1
            address="tb1pvt7lzserh8xd5m6mq0zu9s5wxkpe5wgf5ts56v44jhrr6578hz8saxup5m",
            amount=100_000 - 50_000 - 500 - 490,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
            payment_req_index=0,
        ),
        # Coordinator's output.
        messages.TxOutputType(
            address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
            amount=36_945,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
            payment_req_index=0,
        ),
    ]

    payment_req = make_payment_request(
        client,
        recipient_name="www.example.com",
        outputs=outputs,
        change_addresses=[
            "tb1phkcspf88hge86djxgtwx2wu7ddghsw77d6sd7txtcxncu0xpx22shcydyf",
            "tb1pchruvduckkwuzm5hmytqz85emften5dnmkqu9uhfxwfywaqhuu0qjggqyp",
        ],
    )
    payment_req.amount = None

    with client:
        client.set_expected_responses(
            [
                messages.PreauthorizedRequest(),
                request_input(0),
                request_input(1),
                request_output(0),
                request_payment_req(0),
                request_output(1),
                request_output(2),
                request_output(3),
                request_output(4),
                request_input(0),
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                request_output(2),
                request_output(3),
                request_output(4),
                request_input(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            payment_reqs=[payment_req],
            preauthorized=True,
        )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "010000000001028abbd1cf69e00fbf60fa3ba475dccdbdba4a859ffa6bfd1ee820a75b1be2b7e50000000000ffffffff0ab6ad3ba09261cfb4fa1d3680cb19332a8fe4d9de9ea89aa565bd83a2c082f90100000000ffffffff0550c3000000000000225120e0458118b80a08042d84c4f0356d86863fe2bffc034e839c166ad4e8da7e26ef50c3000000000000225120bdb100a4e7ba327d364642dc653b9e6b51783bde6ea0df2ccbc1a78e3cc1329511e56d0000000000225120c5c7c63798b59dc16e97d916011e99da5799d1b3dd81c2f2e93392477417e71e72bf00000000000022512062fdf14323b9ccda6f5b03c5c2c28e35839a3909a2e14d32b595c63d53c7b88f51900000000000001976a914a579388225827d9f2fe9014add644487808c695d88ac000140c017fce789fa8db54a2ae032012d2dd6d7c76cc1c1a6f00e29b86acbf93022da8aa559009a574792c7b09b2535d288d6e03c6ed169902ed8c4c97626a83fbc1100000000"
    )

    # Test for a second time.
    btc.sign_tx(
        client,
        "Testnet",
        inputs,
        outputs,
        prev_txes=TX_CACHE_TESTNET,
        payment_reqs=[payment_req],
        preauthorized=True,
    )

    # Test for a third time, number of rounds should be exceeded.
    with pytest.raises(TrezorFailure, match="Exceeded number of CoinJoin rounds"):
        btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            payment_reqs=[payment_req],
            preauthorized=True,
        )


def test_sign_tx_spend(client: Client):
    # NOTE: FAKE input tx

    inputs = [
        messages.TxInputType(
            address_n=parse_path("m/10025h/1h/0h/1h/1/0"),
            amount=7_289_000,
            prev_hash=FAKE_TXHASH_f982c0,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDTAPROOT,
        ),
    ]

    outputs = [
        # Our change output.
        messages.TxOutputType(
            # tb1pchruvduckkwuzm5hmytqz85emften5dnmkqu9uhfxwfywaqhuu0qjggqyp
            address_n=parse_path("m/10025h/1h/0h/1h/1/2"),
            amount=7_289_000 - 50_000 - 400,
            script_type=messages.OutputScriptType.PAYTOTAPROOT,
        ),
        # Payment output.
        messages.TxOutputType(
            address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        ),
    ]

    # Ensure that Trezor refuses to spend from CoinJoin without user authorization.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
        )

    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.Other),
                messages.UnlockedPathRequest(),
                request_input(0),
                request_output(0),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_output(0),
                request_output(1),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            unlock_path=SLIP25_PATH,
        )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "010000000001010ab6ad3ba09261cfb4fa1d3680cb19332a8fe4d9de9ea89aa565bd83a2c082f90100000000ffffffff02c8736e0000000000225120c5c7c63798b59dc16e97d916011e99da5799d1b3dd81c2f2e93392477417e71e50c30000000000001976a914a579388225827d9f2fe9014add644487808c695d88ac014006bc29900d39570fca291c038551817430965ac6aa26f286483559e692a14a82cfaf8e57610eae12a5af05ee1e9600acb31de4757349c0e3066701aa78f65d2a00000000"
    )


def test_wrong_coordinator(client: Client):
    # Ensure that a preauthorized GetOwnershipProof fails if the commitment_data doesn't match the coordinator.

    btc.authorize_coinjoin(
        client,
        coordinator="www.example.com",
        max_rounds=10,
        max_coordinator_fee_rate=50_000_000,  # 0.5 %
        max_fee_per_kvbyte=3500,
        n=parse_path("m/10025h/1h/0h/1h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )

    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=b"\x0fwww.example.org" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )


def test_wrong_account_type(client: Client):
    params = {
        "client": client,
        "coordinator": "www.example.com",
        "max_rounds": 10,
        "max_coordinator_fee_rate": 50_000_000,  # 0.5 %
        "max_fee_per_kvbyte": 3500,
        "coin_name": "Testnet",
    }

    # Ensure that Trezor accepts CoinJoin authorizations only for SLIP-0025 paths.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.authorize_coinjoin(
            **params,
            n=parse_path("m/86h/1h/0h"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
        )

    # Ensure that correct parameters succeed.
    btc.authorize_coinjoin(
        **params,
        n=parse_path("m/10025h/1h/0h/1h"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )


def test_cancel_authorization(client: Client):
    # Ensure that a preauthorized GetOwnershipProof fails if the commitment_data doesn't match the coordinator.

    btc.authorize_coinjoin(
        client,
        coordinator="www.example.com",
        max_rounds=10,
        max_coordinator_fee_rate=50_000_000,  # 0.5 %
        max_fee_per_kvbyte=3500,
        n=parse_path("m/10025h/1h/0h/1h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )

    device.cancel_authorization(client)

    with pytest.raises(TrezorFailure, match="No preauthorized operation"):
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=b"\x0fwww.example.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )


def test_get_public_key(client: Client):
    ACCOUNT_PATH = parse_path("m/10025h/1h/0h/1h")
    EXPECTED_XPUB = "xpub6DyhEpXMikKQgH2S1UcRwjYhxHVVLK8ffaABC5E1M1juvdik9t8VsucEnM585ZpiJjiu5uFnpuq21WnkvAH2h8LDMw6jubfX5J2ZggQX1hP"

    # Ensure that user cannot access SLIP-25 path without UnlockPath.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        resp = btc.get_public_node(
            client,
            ACCOUNT_PATH,
            script_type=messages.InputScriptType.SPENDTAPROOT,
        )

    # Get unlock path MAC.
    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.Other),
                messages.UnlockedPathRequest,
                messages.Failure(code=messages.FailureType.ActionCancelled),
            ]
        )
        unlock_path_mac = device.unlock_path(client, n=SLIP25_PATH)

    # Ensure that UnlockPath fails with invalid MAC.
    invalid_unlock_path_mac = bytes([unlock_path_mac[0] ^ 1]) + unlock_path_mac[1:]
    with pytest.raises(TrezorFailure, match="Invalid MAC"):
        resp = btc.get_public_node(
            client,
            ACCOUNT_PATH,
            script_type=messages.InputScriptType.SPENDTAPROOT,
            unlock_path=SLIP25_PATH,
            unlock_path_mac=invalid_unlock_path_mac,
        )

    # Ensure that user does not need to confirm access when path unlock is requested with MAC.
    with client:
        client.set_expected_responses(
            [
                messages.UnlockedPathRequest,
                messages.PublicKey,
            ]
        )
        resp = btc.get_public_node(
            client,
            ACCOUNT_PATH,
            script_type=messages.InputScriptType.SPENDTAPROOT,
            unlock_path=SLIP25_PATH,
            unlock_path_mac=unlock_path_mac,
        )
        assert resp.xpub == EXPECTED_XPUB


def test_get_address(client: Client):
    # Ensure that the SLIP-0025 external chain is inaccessible without user confirmation.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_address(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/0/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            show_display=True,
        )

    # Unlock CoinJoin path.
    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.Other),
                messages.UnlockedPathRequest,
                messages.Failure(code=messages.FailureType.ActionCancelled),
            ]
        )
        unlock_path_mac = device.unlock_path(client, SLIP25_PATH)

    # Ensure that the SLIP-0025 external chain is accessible after user confirmation.
    resp = btc.get_address(
        client,
        "Testnet",
        parse_path("m/10025h/1h/0h/1h/0/0"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
        show_display=True,
        unlock_path=SLIP25_PATH,
        unlock_path_mac=unlock_path_mac,
    )
    assert resp == "tb1pl3y9gf7xk2ryvmav5ar66ra0d2hk7lhh9mmusx3qvn0n09kmaghqh32ru7"

    resp = btc.get_address(
        client,
        "Testnet",
        parse_path("m/10025h/1h/0h/1h/0/1"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
        show_display=False,
        unlock_path=SLIP25_PATH,
        unlock_path_mac=unlock_path_mac,
    )
    assert resp == "tb1p64rqq64rtt7eq6p0htegalcjl2nkjz64ur8xsclc59s5845jty7skp2843"

    # Ensure that the SLIP-0025 internal chain is inaccessible even with user authorization.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_address(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            show_display=True,
            unlock_path=SLIP25_PATH,
            unlock_path_mac=unlock_path_mac,
        )

    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_address(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/1"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            show_display=False,
            unlock_path=SLIP25_PATH,
            unlock_path_mac=unlock_path_mac,
        )

    # Ensure that another SLIP-0025 account is inaccessible with the same MAC.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_address(
            client,
            "Testnet",
            parse_path("m/10025h/1h/1h/1h/0/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            show_display=True,
            unlock_path=SLIP25_PATH,
            unlock_path_mac=unlock_path_mac,
        )


def test_multisession_authorization(client: Client):
    # Authorize CoinJoin with www.example1.com in session 1.
    btc.authorize_coinjoin(
        client,
        coordinator="www.example1.com",
        max_rounds=10,
        max_coordinator_fee_rate=50_000_000,  # 0.5 %
        max_fee_per_kvbyte=3500,
        n=parse_path("m/10025h/1h/0h/1h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )

    # Open a second session.
    session_id1 = client.session_id
    client.init_device(new_session=True)

    # Authorize CoinJoin with www.example2.com in session 2.
    btc.authorize_coinjoin(
        client,
        coordinator="www.example2.com",
        max_rounds=10,
        max_coordinator_fee_rate=50_000_000,  # 0.5 %
        max_fee_per_kvbyte=3500,
        n=parse_path("m/10025h/1h/0h/1h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )

    # Requesting a preauthorized ownership proof for www.example1.com should fail in session 2.
    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=b"\x10www.example1.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )

    # Requesting a preauthorized ownership proof for www.example2.com should succeed in session 2.
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Testnet",
        parse_path("m/10025h/1h/0h/1h/1/0"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
        user_confirmation=True,
        commitment_data=b"\x10www.example2.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        preauthorized=True,
    )

    assert (
        ownership_proof.hex()
        == "534c0019010169d0c751442f4c9adacbd42987121d75b36e3932db217e5bb3784f368f5a4c5d00014097bb2f1f87aea1e809756a6f2ef84109613ccf1bf9b96ffb9305b6193b3942510a8650693ca8af74f0f63401baa384d0c0f7188f1d2df56b91362646c82223a8"
    )

    # Switch back to the first session.
    session_id2 = client.session_id
    client.init_device(session_id=session_id1)

    # Requesting a preauthorized ownership proof for www.example1.com should succeed in session 1.
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Testnet",
        parse_path("m/10025h/1h/0h/1h/1/0"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
        user_confirmation=True,
        commitment_data=b"\x10www.example1.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        preauthorized=True,
    )

    assert (
        ownership_proof.hex()
        == "534c0019010169d0c751442f4c9adacbd42987121d75b36e3932db217e5bb3784f368f5a4c5d00014078fefa8243283cd575c885f97fd2e3405c934ab4d3e415ff5fe27d49f347bbb592e03ff6195f46c94a592799748c8dd7daea8b3fc4b2011b7e58a74ee296853b"
    )

    # Requesting a preauthorized ownership proof for www.example2.com should fail in session 1.
    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=b"\x10www.example2.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )

    # Cancel the authorization in session 1.
    device.cancel_authorization(client)

    # Requesting a preauthorized ownership proof should fail now.
    with pytest.raises(TrezorFailure, match="No preauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=b"\x10www.example1.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )

    # Switch to the second session.
    client.init_device(session_id=session_id2)

    # Requesting a preauthorized ownership proof for www.example2.com should still succeed in session 2.
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Testnet",
        parse_path("m/10025h/1h/0h/1h/1/0"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
        user_confirmation=True,
        commitment_data=b"\x10www.example2.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        preauthorized=True,
    )
