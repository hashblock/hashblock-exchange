

#include <stdio.h>
#include <stdlib.h>
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

typedef struct {

	//	Penderson commit vars and outcomes
	secp256k1_context 				*sign_ctx;
	secp256k1_context 				*verify_ctx;
	secp256k1_context 				*both_ctx;
	uint64_t 						value;
	unsigned char 					*blind_ptr;
	secp256k1_pedersen_commitment	commitment;

	//	Range proof vars and outcomes
	unsigned char 					*message_ptr;
	uint64_t 						message_len;
	uint64_t 						min_value;
	unsigned char 					*nonce;
	int 							exponent; // fixed 0 for most private
	int 							min_bits; // fixed 0 for auto
	unsigned char 					*extra_commit; // Fixed NULL for now
	size_t 							extra_commit_len; // fixed 0 for no extra
	int 							proof_len; // In buffer size, out length in buffer proof
	unsigned char 					proof[5134+1];
} zkproof;

int create_commitment(zkproof *zkp) {
	int commit_res = secp256k1_pedersen_commit(zkp->sign_ctx, &zkp->commitment,
		zkp->blind_ptr, zkp->value, secp256k1_generator_h);
	return commit_res;
}

int create_proof(zkproof *zkp) {
	int proof_res = secp256k1_rangeproof_sign(
		zkp->both_ctx,
		zkp->proof,
		&zkp->proof_len,
		zkp->min_value,
		&zkp->commitment,
		zkp->blind_ptr,
		zkp->nonce,
		zkp->exponent,
		zkp->min_bits,
		zkp->value,
		zkp->message_ptr,
		zkp->message_len,
		zkp->extra_commit,
		zkp->extra_commit_len,
		secp256k1_generator_h);
	return proof_res;
}

int verify_proof(zkproof *zkp) {
	int verify_res = 0;
	return verify_res;
}

int main( int c , char *argv[]) {
	(void)c;
	(void)argv;
	zkproof 	test;
	test.sign_ctx = secp256k1_context_create(SECP256K1_CONTEXT_SIGN);
	test.verify_ctx = secp256k1_context_create(SECP256K1_CONTEXT_VERIFY);
    test.both_ctx = secp256k1_context_create(SECP256K1_CONTEXT_SIGN | SECP256K1_CONTEXT_VERIFY);
	int32_t ecount=0;

	secp256k1_context_set_error_callback(test.sign_ctx, counting_illegal_callback_fn, &ecount);
	secp256k1_context_set_error_callback(test.verify_ctx, counting_illegal_callback_fn, &ecount);
	secp256k1_context_set_error_callback(test.both_ctx, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(test.sign_ctx, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(test.verify_ctx, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(test.both_ctx, counting_illegal_callback_fn, &ecount);

    const unsigned char blind[32] = "   i am not a blinding factor   ";
    test.blind_ptr = blind;
    test.value = 80;

    // Create a signed commitment for value N
    int cresult = create_commitment(&test);
    printf("Commitment result = %i\n", cresult);
    printf("Commitment buffer = %s\n", test.commitment.data);
    printf("Commitment ecount = %i\n", ecount);

    unsigned char message[120] = "When I see my own likeness in the depths of someone else's consciousness,  I always experience a moment of panic.";
    test.message_ptr = message;
    test.message_len = sizeof(message);
    test.nonce = test.commitment.data;
    test.min_value = 40;
    test.min_bits = test.exponent = 0;
    test.extra_commit = NULL;
    test.extra_commit_len = 0;
    test.proof_len = sizeof(test.proof);

    // Create a signed proof
    int presult = create_proof(&test);
    printf("Proof result = %i\n", presult);
    printf("Proof buffer size = %i\n", test.proof_len);
    printf("Proof ecount = %i\n", ecount);


    secp256k1_context_destroy(test.sign_ctx);
    secp256k1_context_destroy(test.verify_ctx);
    secp256k1_context_destroy(test.both_ctx);

	return 0;
}