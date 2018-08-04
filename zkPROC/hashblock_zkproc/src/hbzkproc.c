

#include <stdio.h>
#include <stdlib.h>
#include <secp256k1.h>

int main( int c , char *argv[]) {

	unsigned int flags =  SECP256K1_CONTEXT_SIGN;
	secp256k1_context* ctx = secp256k1_context_create(flags);

	char* turingsk = "f5109ec8e2b1bec395ca7e24e27aaf22bc0afaeef3e39314591fd488fa6805cd";

	

	printf("hello zk-protocol");
	return 0;
}