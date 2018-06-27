

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
    // printf("%s\n", str );
    (void)str;
    p = data;
    (*p)++;
}

void check_serialize(const secp256k1_context *ctx, const secp256k1_pedersen_commitment *commitment) {
    unsigned char serialized_commit_out[33];
	printf("Succesful commitment creation\n");
	printf("RAW: %s\n",commitment->data);
	CHECK(secp256k1_pedersen_commitment_serialize(ctx, serialized_commit_out, commitment) !=0);
	printf("SERIALIZED: %s\n",serialized_commit_out);
}


int main( int c , char *argv[]) {
    secp256k1_context *none = secp256k1_context_create(SECP256K1_CONTEXT_NONE);
 	secp256k1_context *sign = secp256k1_context_create(SECP256K1_CONTEXT_SIGN);
    secp256k1_context *vrfy = secp256k1_context_create(SECP256K1_CONTEXT_VERIFY);
    secp256k1_context *both = secp256k1_context_create(SECP256K1_CONTEXT_SIGN | SECP256K1_CONTEXT_VERIFY);
	int32_t ecount=0;

	secp256k1_context_set_error_callback(none, counting_illegal_callback_fn, &ecount);
	secp256k1_context_set_error_callback(sign, counting_illegal_callback_fn, &ecount);
	secp256k1_context_set_error_callback(vrfy, counting_illegal_callback_fn, &ecount);
	secp256k1_context_set_error_callback(both, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(none, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(sign, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(vrfy, counting_illegal_callback_fn, &ecount);
    secp256k1_context_set_illegal_callback(both, counting_illegal_callback_fn, &ecount);

	secp256k1_pedersen_commitment commit;
    const secp256k1_pedersen_commitment *commit_ptr = &commit;
    const unsigned char blind[32] = "   i am not a blinding factor   ";
    const unsigned char *blind_ptr = blind;
    size_t blindlen = sizeof(blind);
    uint64_t val = 256;
    secp256k1_generator value_gen;

    // secp256k1-zkp examples
    CHECK(secp256k1_pedersen_commit(none, &commit, blind, val, secp256k1_generator_h) == 0);
    if( ecount == 1) {
    	printf("Penderson commit with ctx = none success\n");
    }
    else {
    	printf("Not so good %i\n", ecount);
    	printf("%s\n",commit.data);
    }
    CHECK(secp256k1_pedersen_commit(vrfy, &commit, blind, val, secp256k1_generator_h) == 0);
    if( ecount == 2) {
    	printf("Penderson commit with ctx = verify success\n");
    }
    else {
    	printf("Not so good %i\n", ecount);
    	printf("%s\n",commit.data);
    }
    CHECK(secp256k1_pedersen_commit(sign, &commit, blind, val, secp256k1_generator_h) != 0);
    if( ecount == 2) {
    	printf("Penderson commit with ctx = sign success\n");
    	check_serialize(sign, &commit);
    }
    else {
    	printf("Not so good %i\n", ecount);
    	printf("%s\n",commit.data);
    }

    secp256k1_context_destroy(none);
    secp256k1_context_destroy(sign);
    secp256k1_context_destroy(vrfy);
    secp256k1_context_destroy(both);

	return 0;
}