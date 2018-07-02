

#include <stdio.h>
#include <stdlib.h>
#include <secp256k1_generator.h>
#include <secp256k1_rangeproof.h>


#ifdef DETERMINISTIC
#define TEST_FAILURE(msg) do { \
    fprintf(stderr, "%s\n", msg); \
    abort(); \
} while(0);
#else
#define TEST_FAILURE(msg) do { \
    fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, msg); \
    abort(); \
} while(0)
#endif

#ifdef HAVE_BUILTIN_EXPECT
#define EXPECT(x,c) __builtin_expect((x),(c))
#else
#define EXPECT(x,c) (x)
#endif

#ifdef DETERMINISTIC
#define CHECK(cond) do { \
    if (EXPECT(!(cond), 0)) { \
        TEST_FAILURE("test condition failed"); \
    } \
} while(0)
#else
#define CHECK(cond) do { \
    if (EXPECT(!(cond), 0)) { \
        TEST_FAILURE("test condition failed: " #cond); \
    } \
} while(0)
#endif

static void counting_illegal_callback_fn(const char* str, void* data) {
    /* Dummy callback function that just counts. */
    int32_t *p;
    printf("CICFN: %s\n", str );
    //(void)str;
    p = data;
    (*p)++;
}


void test_rangeproof(secp256k1_context *sign, secp256k1_context *verify, secp256k1_context *both) {

	//	Setup commitment

    secp256k1_pedersen_commitment	commitment;
    //const unsigned char 			blind[32]="01234567890123456789012345678901";
    const unsigned char blind[32]={0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
    	0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
    	0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
    	0x00, 0x01};
    uint64_t 						value = 65;

	int commit_res = secp256k1_pedersen_commit(
		sign,
		&commitment,
		blind,
		value,
		&secp256k1_generator_const_g,
		&secp256k1_generator_const_h);

	printf("Commitment RC = %i\n", commit_res);
    printf("Commitment = ");
    for(uint64_t i=0; i < sizeof(commitment.data); i++)
    	printf("%x", commitment.data[i]);

    //	Setup proof

    const unsigned char message[120] = "When I see my own likeness in the depths of someone else's consciousness,  I always experience a moment of panic.";
    size_t 				message_len = sizeof(message);
    unsigned char 		proof[5134];
    uint64_t 			proof_len = sizeof(proof);
    uint64_t 			min_value = 35;
    int   				min_bits = 32;
    int 				exponent = 0;
    int 				mantissa = 0;

	int proof_res = secp256k1_rangeproof_sign(
		both,
		proof,
		&proof_len,
		min_value,
		&commitment,
		blind,
		commitment.data,
		exponent,
		min_bits,
		value,
		message,
		message_len,
		NULL,
		0,
		&secp256k1_generator_const_h);

	printf("Proof RC = %i\n", proof_res);
	printf("Proof len = %lu\n", proof_len);
    for(uint64_t i=0; i < proof_len; i++)
    	printf("%x", proof[i]);
    printf("\n");

    //	Setup verify
	uint64_t 			verify_min=0;
	uint64_t 			verify_max=0;

	int verify_res = secp256k1_rangeproof_verify(
		verify,
		&verify_min,
		&verify_max,
		&commitment,
		proof,
		proof_len,
		NULL,
		0,
		&secp256k1_generator_const_h);

	printf("Verify RC = %i\n", verify_res);
    printf("Verify min value = %lu\n", verify_min);
    printf("Verify max value = %lu\n", verify_max);

    //	Setup info

	int info_res = secp256k1_rangeproof_info(
		both,
		&exponent,
		&mantissa,
		&verify_min,
		&verify_max,
		proof,
		proof_len);

	printf("Info RC = %i\n", info_res);
    printf("Info min value = %lu\n", verify_min);
    printf("Info max value = %lu\n", verify_max);

}

/*
	ARTHUR... PUT YOUR STUFF HERE
*/

void test_bulletproof(secp256k1_context *sign, secp256k1_context *verify, secp256k1_context *both) {
}

int main( int c , char *argv[]) {
	(void)c;
	(void)argv;
	secp256k1_context *sign_ctx = secp256k1_context_create(SECP256K1_CONTEXT_SIGN);
	secp256k1_context *verify_ctx = secp256k1_context_create(SECP256K1_CONTEXT_VERIFY);
    secp256k1_context *both_ctx = secp256k1_context_create(SECP256K1_CONTEXT_SIGN | SECP256K1_CONTEXT_VERIFY);
	int32_t ecount=0;

	secp256k1_context_set_error_callback(sign_ctx, counting_illegal_callback_fn, &ecount);
	secp256k1_context_set_error_callback(verify_ctx, counting_illegal_callback_fn, &ecount);
	secp256k1_context_set_error_callback(both_ctx, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(sign_ctx, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(verify_ctx, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(both_ctx, counting_illegal_callback_fn, &ecount);

    test_rangeproof(sign_ctx, verify_ctx, both_ctx);
    test_bulletproof(sign_ctx, verify_ctx, both_ctx);


    // Destroy these contexts
    secp256k1_context_destroy(sign_ctx);
    secp256k1_context_destroy(verify_ctx);
    secp256k1_context_destroy(both_ctx);

	return 0;
}